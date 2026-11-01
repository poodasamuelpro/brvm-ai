"""Importe des observations macroéconomiques BCEAO/UEMOA depuis un JSON sourcé."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from brvm_ia.base_de_donnees.moteur import GestionnaireBaseDeDonnees  # noqa: E402
from brvm_ia.configuration import obtenir_parametres  # noqa: E402


def _date(value: Any, field: str, line: int) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as error:
        raise ValueError(f"Ligne {line}: {field} doit être YYYY-MM-DD.") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-code", required=True)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    contenu = args.input.read_bytes()
    payload: Any = json.loads(contenu)
    if not isinstance(payload, list):
        parser.error("Le fichier JSON doit contenir une liste d'observations.")
    for line, observation in enumerate(payload, 1):
        for field in ("series_code", "country_or_zone", "period_start", "period_end", "value", "unit_code"):
            if observation.get(field) in (None, ""):
                parser.error(f"Ligne {line}: {field} requis.")
        observation["period_start"] = _date(observation["period_start"], "period_start", line)
        observation["period_end"] = _date(observation["period_end"], "period_end", line)
        observation["value"] = Decimal(str(observation["value"]))
        if observation["period_end"] < observation["period_start"]:
            parser.error(f"Ligne {line}: période inversée.")
    now = datetime.now(UTC)
    digest = hashlib.sha256(contenu).hexdigest()
    key = f"{args.source_code}:{digest}"
    with GestionnaireBaseDeDonnees(obtenir_parametres()) as gestionnaire:
        with gestionnaire.session() as session:
            source_id = session.execute(text("""
                INSERT INTO brvm.data_source (code, name, source_type, base_url)
                VALUES (:code, :name, 'macro_officielle', :url)
                ON CONFLICT (code) DO UPDATE SET name=EXCLUDED.name, base_url=EXCLUDED.base_url
                RETURNING source_id
            """), {"code": args.source_code.upper(), "name": args.source_name, "url": args.source_url}).scalar_one()
            document_id = session.execute(text("""
                INSERT INTO brvm.source_document
                    (source_id, external_identifier, source_url, mime_type, content_sha256, retrieved_at)
                VALUES (:source, :key, :url, 'application/json', :hash, :now)
                ON CONFLICT (source_id, external_identifier)
                DO UPDATE SET retrieved_at=EXCLUDED.retrieved_at
                RETURNING source_document_id
            """), {"source": source_id, "key": key, "url": args.source_url, "hash": digest, "now": now}).scalar_one()
            raw_id = session.execute(text("""
                SELECT raw_ingest_record_id FROM brvm.raw_ingest_record
                WHERE source_id=:source AND dataset_kind='macro_observations'
                  AND source_record_key=:key AND payload_sha256=:hash
                ORDER BY received_at DESC LIMIT 1
            """), {"source": source_id, "key": key, "hash": digest}).scalar_one_or_none()
            existing = raw_id is not None
            if raw_id is None:
                raw_id = session.execute(text("""
                    INSERT INTO brvm.raw_ingest_record
                        (source_id, source_document_id, dataset_kind, source_record_key, raw_payload,
                         payload_sha256, received_at, processing_status, processed_at)
                    VALUES (:source, :document, 'macro_observations', :key, CAST(:payload AS jsonb),
                            :hash, :now, 'normalized', :now)
                    RETURNING raw_ingest_record_id
                """), {"source": source_id, "document": document_id, "key": key,
                       "payload": contenu.decode(), "hash": digest, "now": now}).scalar_one()
            inserted = 0
            if not existing:
                for observation in payload:
                    session.execute(text("""
                        INSERT INTO brvm.macro_observation
                            (source_id, source_document_id, raw_ingest_record_id, series_code,
                             country_or_zone, statistical_period_start, statistical_period_end,
                             published_at, value, unit_code, validation_status)
                        VALUES (:source, :document, :raw, :series, :zone, :period_start, :period_end,
                                :published, :value, :unit, :status)
                    """), {"source": source_id, "document": document_id, "raw": raw_id,
                           "series": observation["series_code"].strip(),
                           "zone": observation["country_or_zone"].strip(),
                           "period_start": observation["period_start"],
                           "period_end": observation["period_end"],
                           "published": observation.get("published_at"),
                           "value": observation["value"], "unit": observation["unit_code"].strip(),
                           "status": observation.get("validation_status", "pending")})
                    inserted += 1
    print(f"Observations lues : {len(payload)} ; observations enregistrées : {inserted}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
