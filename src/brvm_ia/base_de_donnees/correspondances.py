"""Correspondances vérifiées entre titres BRVM et identifiants fournisseurs."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from brvm_ia.exceptions import ErreurValidationDonnees


def enregistrer_correspondance(
    session: Session,
    *,
    security_id: UUID,
    source_id: UUID,
    identifier_type: str,
    identifier: str,
    source_document_id: UUID | None = None,
    verification_status: str = "verified",
    valid_from: date | None = None,
    valid_to: date | None = None,
    notes: str | None = None,
) -> UUID:
    """Enregistre une correspondance fournie explicitement par l'opérateur."""
    if verification_status not in {"pending", "verified", "rejected"}:
        raise ErreurValidationDonnees("Statut de correspondance non autorisé.")
    if not identifier.strip() or identifier != identifier.strip():
        raise ErreurValidationDonnees("L'identifiant fournisseur doit être non vide et normalisé.")
    if valid_from is not None and valid_to is not None and valid_to < valid_from:
        raise ErreurValidationDonnees("La fin de validité doit être postérieure au début.")

    row = session.execute(
        text(
            """
            INSERT INTO brvm.security_external_identifier
                (security_id, source_id, identifier_type, identifier,
                 verification_status, source_document_id, valid_from, valid_to, notes)
            VALUES (:security_id, :source_id, :identifier_type, :identifier,
                    :verification_status, :source_document_id, :valid_from, :valid_to, :notes)
            ON CONFLICT (source_id, identifier_type, identifier)
            WHERE valid_to IS NULL AND verification_status <> 'rejected'
            DO UPDATE SET
                security_id = EXCLUDED.security_id,
                verification_status = EXCLUDED.verification_status,
                source_document_id = EXCLUDED.source_document_id,
                valid_from = EXCLUDED.valid_from,
                notes = EXCLUDED.notes
            RETURNING security_external_identifier_id
            """
        ),
        {
            "security_id": security_id,
            "source_id": source_id,
            "identifier_type": identifier_type,
            "identifier": identifier,
            "verification_status": verification_status,
            "source_document_id": source_document_id,
            "valid_from": valid_from,
            "valid_to": valid_to,
            "notes": notes,
        },
    ).scalar_one()
    return row


def resoudre_correspondance(
    session: Session,
    *,
    source_id: UUID,
    identifier_type: str,
    identifier: str,
    date_observation: date,
) -> UUID | None:
    """Retourne un titre uniquement si la correspondance externe est vérifiée."""
    return session.execute(
        text(
            """
            SELECT security_id
            FROM brvm.security_external_identifier
            WHERE source_id = :source_id
              AND identifier_type = :identifier_type
              AND identifier = :identifier
              AND verification_status = 'verified'
              AND (valid_from IS NULL OR valid_from <= :date_observation)
              AND (valid_to IS NULL OR valid_to >= :date_observation)
            ORDER BY valid_from DESC NULLS LAST
            LIMIT 1
            """
        ),
        {
            "source_id": source_id,
            "identifier_type": identifier_type,
            "identifier": identifier,
            "date_observation": date_observation,
        },
    ).scalar_one_or_none()
