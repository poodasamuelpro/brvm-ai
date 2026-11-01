"""Importe des faits financiers structurés fournis par une publication officielle.

Le JSON doit contenir une liste de faits avec symbole BRVM, période, périmètre,
metric_code, value et unit_code. Les faits restent ``pending`` par défaut.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from brvm_ia.base_de_donnees.moteur import GestionnaireBaseDeDonnees  # noqa: E402
from brvm_ia.collecte.fondamentaux import enregistrer_faits, lire_faits  # noqa: E402
from brvm_ia.configuration import obtenir_parametres  # noqa: E402


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
        parser.error("Le fichier JSON doit contenir une liste de faits.")
    faits = lire_faits(payload)
    maintenant = datetime.now(UTC)
    empreinte = hashlib.sha256(contenu).hexdigest()
    external_identifier = f"{args.source_code}:{empreinte}"

    with GestionnaireBaseDeDonnees(obtenir_parametres()) as gestionnaire:
        with gestionnaire.session() as session:
            source_id = session.execute(
                text(
                    """
                    INSERT INTO brvm.data_source (code, name, source_type, base_url)
                    VALUES (:code, :name, 'rapport_financier', :url)
                    ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, base_url = EXCLUDED.base_url
                    RETURNING source_id
                    """
                ),
                {"code": args.source_code.upper(), "name": args.source_name, "url": args.source_url},
            ).scalar_one()
            document_id = session.execute(
                text(
                    """
                    INSERT INTO brvm.source_document
                        (source_id, external_identifier, source_url, mime_type,
                         content_sha256, retrieved_at)
                    VALUES (:source_id, :external_identifier, :source_url,
                            'application/json', :hash, :retrieved_at)
                    ON CONFLICT (source_id, external_identifier)
                    DO UPDATE SET retrieved_at = EXCLUDED.retrieved_at
                    RETURNING source_document_id
                    """
                ),
                {
                    "source_id": source_id,
                    "external_identifier": external_identifier,
                    "source_url": args.source_url,
                    "hash": empreinte,
                    "retrieved_at": maintenant,
                },
            ).scalar_one()
            raw_id = session.execute(
                text(
                    """
                    SELECT raw_ingest_record_id FROM brvm.raw_ingest_record
                    WHERE source_id = :source_id AND dataset_kind = 'financial_facts'
                      AND source_record_key = :record_key AND payload_sha256 = :hash
                    ORDER BY received_at DESC LIMIT 1
                    """
                ),
                {"source_id": source_id, "record_key": external_identifier, "hash": empreinte},
            ).scalar_one_or_none()
            raw_existant = raw_id is not None
            if raw_id is None:
                raw_id = session.execute(
                    text(
                        """
                        INSERT INTO brvm.raw_ingest_record
                            (source_id, source_document_id, dataset_kind, source_record_key,
                             raw_payload, payload_sha256, received_at, processing_status, processed_at)
                        VALUES (:source_id, :document_id, 'financial_facts', :record_key,
                                CAST(:payload AS jsonb), :hash, :received_at, 'normalized', :processed_at)
                        RETURNING raw_ingest_record_id
                        """
                    ),
                    {
                        "source_id": source_id,
                        "document_id": document_id,
                        "record_key": external_identifier,
                        "payload": contenu.decode("utf-8"),
                        "hash": empreinte,
                        "received_at": maintenant,
                        "processed_at": maintenant,
                    },
                ).scalar_one()
            inserted = 0 if raw_existant else enregistrer_faits(
                session, source_id=source_id, raw_ingest_record_id=raw_id, faits=faits
            )
    print(f"Faits lus : {len(faits)} ; faits enregistrés : {inserted}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
