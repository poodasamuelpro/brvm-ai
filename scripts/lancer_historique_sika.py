"""Collecte et enregistrement d'un historique SIKA dans le schéma brvm.

Exemple:
    ACTIVER_BASE_DE_DONNEES=true BASE_DE_DONNEES_URL=... \
    python scripts/lancer_historique_sika.py --ticker SNTS.sn \
      --debut 2026-07-01 --fin 2026-10-02

L'URL de base est uniquement lue depuis l'environnement/.env et n'est jamais
écrite dans Git ni dans les journaux.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sqlalchemy import text  # noqa: E402

from brvm_ia.base_de_donnees.moteur import GestionnaireBaseDeDonnees  # noqa: E402
from brvm_ia.collecte.sources.sika_finance import (  # noqa: E402
    CODE_SOURCE_SIKA,
    BarreHistoriqueSIKA,
    recuperer_historique,
)
from brvm_ia.configuration import obtenir_parametres  # noqa: E402

CODE_PIPELINE = "collecte_sika_historique"
VERSION_PIPELINE = "1"
DATASET = "sika_historique_ohlcv"


def _json_barre(barre: BarreHistoriqueSIKA) -> dict[str, str | None]:
    return {
        "ticker_sika": barre.ticker_sika,
        "date": barre.date_seance.isoformat(),
        "open": str(barre.ouverture),
        "high": str(barre.plus_haut),
        "low": str(barre.plus_bas),
        "close": str(barre.cloture),
        "volume": str(barre.volume_titres),
        "volume_fcfa": str(barre.volume_fcfa) if barre.volume_fcfa is not None else None,
        "variation_pct": str(barre.variation_pct) if barre.variation_pct is not None else None,
    }


def enregistrer(ticker: str, debut: date, fin: date) -> tuple[int, int]:
    barres = recuperer_historique(ticker, debut, fin)
    if not barres:
        return 0, 0
    maintenant = datetime.now(UTC)
    representation = [_json_barre(barre) for barre in barres]
    empreinte = hashlib.sha256(
        json.dumps(representation, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()
    identifiant = f"{ticker}:{debut.isoformat()}:{fin.isoformat()}:{empreinte}"
    symbole = ticker.split(".", 1)[0]

    with (
        GestionnaireBaseDeDonnees(obtenir_parametres()) as gestionnaire,
        gestionnaire.session() as session,
    ):
        source_id = session.execute(
            text(
                """INSERT INTO brvm.data_source
                    (code,name,source_type,base_url,terms_url)
                    VALUES (:code,:name,'site_web_public',:base,:terms)
                    ON CONFLICT (code) DO UPDATE SET code=EXCLUDED.code
                    RETURNING source_id"""
            ),
            {
                "code": CODE_SOURCE_SIKA,
                "name": "SIKA Finance — historiques de marché",
                "base": "https://www.sikafinance.com",
                "terms": "https://www.sikafinance.com/politique_confidentialite",
            },
        ).scalar_one()
        deja = session.execute(
            text(
                "SELECT source_document_id FROM brvm.source_document "
                "WHERE source_id=:source AND external_identifier=:ident"
            ),
            {"source": source_id, "ident": identifiant},
        ).scalar_one_or_none()
        if deja is not None:
            return len(barres), 0
        document_id = session.execute(
            text(
                """INSERT INTO brvm.source_document
                    (source_id,external_identifier,source_url,mime_type,content_sha256,retrieved_at)
                    VALUES (:source,:ident,:url,'application/json',:hash,:retrieved)
                    RETURNING source_document_id"""
            ),
            {
                "source": source_id,
                "ident": identifiant,
                "url": f"https://www.sikafinance.com/marches/historiques/{ticker}",
                "hash": empreinte,
                "retrieved": maintenant,
            },
        ).scalar_one()
        definition_id = session.execute(
            text(
                """INSERT INTO brvm.pipeline_definition
                    (code,version,description,is_enabled)
                    VALUES (:code,:version,:description,true)
                    ON CONFLICT (code,version) DO UPDATE SET code=EXCLUDED.code
                    RETURNING pipeline_definition_id"""
            ),
            {
                "code": CODE_PIPELINE,
                "version": VERSION_PIPELINE,
                "description": "Collecte historique SIKA Finance",
            },
        ).scalar_one()
        run_id = session.execute(
            text(
                """INSERT INTO brvm.pipeline_run
                    (pipeline_definition_id,run_status,parameters,started_at,finished_at,
                     rows_processed,rows_rejected)
                    VALUES (:definition,'succeeded',CAST(:parameters AS jsonb),:now,:now,:rows,0)
                    RETURNING pipeline_run_id"""
            ),
            {
                "definition": definition_id,
                "parameters": json.dumps(
                    {"ticker": ticker, "debut": debut.isoformat(), "fin": fin.isoformat()}
                ),
                "now": maintenant,
                "rows": len(barres),
            },
        ).scalar_one()
        session.execute(
            text(
                "INSERT INTO brvm.pipeline_run_source"
                "(pipeline_run_id,source_id,source_document_id) VALUES (:run,:source,:doc)"
            ),
            {"run": run_id, "source": source_id, "doc": document_id},
        )
        security_id = session.execute(
            text(
                """SELECT ss.security_id FROM brvm.security_symbol_history ss
                    JOIN brvm.security s ON s.security_id=ss.security_id
                        AND s.market_id=ss.market_id
                    WHERE ss.symbol=:symbol ORDER BY ss.valid_from DESC LIMIT 1"""
            ),
            {"symbol": symbole},
        ).scalar_one_or_none()
        if security_id is None:
            raise RuntimeError(f"Correspondance BRVM non vérifiée pour {ticker}.")
        inserted = 0
        for barre in barres:
            payload = _json_barre(barre)
            payload_text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            raw_id = session.execute(
                text(
                    """INSERT INTO brvm.raw_ingest_record
                        (source_id,source_document_id,dataset_kind,source_record_key,raw_payload,
                         payload_sha256,published_at,processing_status,processed_at)
                        VALUES (:source,:doc,:dataset,:key,CAST(:payload AS jsonb),:hash,:published,
                                'normalized',:processed)
                        RETURNING raw_ingest_record_id"""
                ),
                {
                    "source": source_id,
                    "doc": document_id,
                    "dataset": DATASET,
                    "key": f"{ticker}:{barre.date_seance.isoformat()}",
                    "payload": payload_text,
                    "hash": hashlib.sha256(payload_text.encode()).hexdigest(),
                    "published": datetime.combine(barre.date_seance, time.min, tzinfo=UTC),
                    "processed": maintenant,
                },
            ).scalar_one()
            exists = session.execute(
                text(
                    """SELECT market_bar_id FROM brvm.market_bar
                        WHERE security_id=:security AND source_id=:source AND interval_code='1d'
                          AND market_date=:market_date AND validation_status='validated'"""
                ),
                {
                    "security": security_id,
                    "source": source_id,
                    "market_date": barre.date_seance,
                },
            ).scalar_one_or_none()
            if exists is not None:
                continue
            session.execute(
                text(
                    """INSERT INTO brvm.market_bar
                        (security_id,source_id,raw_ingest_record_id,interval_code,period_start,
                         period_end,market_date,opening_price,high_price,low_price,closing_price,
                         volume,traded_value,validation_status)
                        VALUES (:security,:source,:raw,'1d',:start,:end,:market_date,:opening,
                                :high,:low,:closing,:volume,:value,'validated')"""
                ),
                {
                    "security": security_id,
                    "source": source_id,
                    "raw": raw_id,
                    "start": datetime.combine(barre.date_seance, time.min, tzinfo=UTC),
                    "end": datetime.combine(barre.date_seance, time.min, tzinfo=UTC)
                    + timedelta(days=1),
                    "market_date": barre.date_seance,
                    "opening": barre.ouverture,
                    "high": barre.plus_haut,
                    "low": barre.plus_bas,
                    "closing": barre.cloture,
                    "volume": barre.volume_titres,
                    "value": barre.volume_fcfa,
                },
            )
            inserted += 1
    return len(barres), inserted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticker", action="append", required=True)
    parser.add_argument("--debut", type=date.fromisoformat, required=True)
    parser.add_argument("--fin", type=date.fromisoformat, required=True)
    args = parser.parse_args()
    total = [enregistrer(ticker, args.debut, args.fin) for ticker in args.ticker]
    print(f"SIKA: {sum(x[0] for x in total)} lignes validées, {sum(x[1] for x in total)} insérées.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
