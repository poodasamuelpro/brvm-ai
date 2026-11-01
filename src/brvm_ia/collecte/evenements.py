"""Validation et persistance d'événements financiers fournis par une source."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class EvenementFinancier:
    security_symbol: str
    action_type: str
    announced_at: datetime | None = None
    ex_date: date | None = None
    record_date: date | None = None
    effective_date: date | None = None
    payment_date: date | None = None
    cash_amount_per_share: Decimal | None = None
    currency_code: str | None = None
    ratio_numerator: Decimal | None = None
    ratio_denominator: Decimal | None = None
    description: str | None = None
    validation_status: str = "pending"


def lire_evenements(payload: list[dict[str, Any]]) -> tuple[EvenementFinancier, ...]:
    """Convertit un payload source en événements sûrs; aucune valeur n'est inventée."""
    resultat: list[EvenementFinancier] = []
    for index, ligne in enumerate(payload, start=1):
        symbole = _texte(ligne.get("security_symbol"), "security_symbol", index)
        action_type = _texte(ligne.get("action_type"), "action_type", index).lower()
        statut = str(ligne.get("validation_status", "pending")).strip().lower()
        if statut not in {"pending", "validated", "rejected", "quarantined"}:
            raise ValueError(f"Ligne {index}: validation_status invalide.")
        currency = ligne.get("currency_code")
        if currency is not None:
            currency = _texte(currency, "currency_code", index).upper()
        amount = _decimal(ligne.get("cash_amount_per_share"), "cash_amount_per_share", index)
        numerator = _decimal(ligne.get("ratio_numerator"), "ratio_numerator", index)
        denominator = _decimal(ligne.get("ratio_denominator"), "ratio_denominator", index)
        if amount is not None and currency is None:
            raise ValueError(f"Ligne {index}: currency_code requis avec un montant.")
        if (numerator is None) != (denominator is None):
            raise ValueError(f"Ligne {index}: ratio incomplet.")
        resultat.append(
            EvenementFinancier(
                security_symbol=symbole,
                action_type=action_type,
                announced_at=_datetime(ligne.get("announced_at"), "announced_at", index),
                ex_date=_date(ligne.get("ex_date"), "ex_date", index),
                record_date=_date(ligne.get("record_date"), "record_date", index),
                effective_date=_date(ligne.get("effective_date"), "effective_date", index),
                payment_date=_date(ligne.get("payment_date"), "payment_date", index),
                cash_amount_per_share=amount,
                currency_code=currency,
                ratio_numerator=numerator,
                ratio_denominator=denominator,
                description=ligne.get("description"),
                validation_status=statut,
            )
        )
    return tuple(resultat)


def enregistrer_evenements(
    session: Session,
    *,
    source_id: UUID,
    source_document_id: UUID,
    raw_ingest_record_id: UUID,
    evenements: tuple[EvenementFinancier, ...],
) -> int:
    """Enregistre les événements après résolution exacte du symbole BRVM."""
    inseres = 0
    for evenement in evenements:
        security_id = session.execute(
            text(
                """
                SELECT security_id
                FROM brvm.security_symbol_history
                WHERE symbol = :symbol
                  AND valid_from <= COALESCE(:event_date, CURRENT_DATE)
                  AND (valid_to IS NULL OR valid_to >= COALESCE(:event_date, CURRENT_DATE))
                ORDER BY valid_from DESC
                LIMIT 1
                """
            ),
            {
                "symbol": evenement.security_symbol,
                "event_date": evenement.ex_date or evenement.effective_date,
            },
        ).scalar_one_or_none()
        if security_id is None:
            raise ValueError(f"Symbole BRVM non résolu : {evenement.security_symbol}.")
        session.execute(
            text(
                """
                INSERT INTO brvm.corporate_action
                    (security_id, source_id, raw_ingest_record_id, action_type,
                     announced_at, ex_date, record_date, effective_date, payment_date,
                     cash_amount_per_share, currency_code, ratio_numerator,
                     ratio_denominator, description, validation_status)
                VALUES (:security_id, :source_id, :raw_id, :action_type,
                        :announced_at, :ex_date, :record_date, :effective_date, :payment_date,
                        :amount, :currency, :numerator, :denominator, :description, :status)
                """
            ),
            {
                "security_id": security_id,
                "source_id": source_id,
                "raw_id": raw_ingest_record_id,
                "action_type": evenement.action_type,
                "announced_at": evenement.announced_at,
                "ex_date": evenement.ex_date,
                "record_date": evenement.record_date,
                "effective_date": evenement.effective_date,
                "payment_date": evenement.payment_date,
                "amount": evenement.cash_amount_per_share,
                "currency": evenement.currency_code,
                "numerator": evenement.ratio_numerator,
                "denominator": evenement.ratio_denominator,
                "description": evenement.description,
                "status": evenement.validation_status,
            },
        )
        inseres += 1
    return inseres


def _texte(valeur: Any, nom: str, ligne: int) -> str:
    if not isinstance(valeur, str) or not valeur.strip():
        raise ValueError(f"Ligne {ligne}: {nom} requis.")
    return valeur.strip()


def _decimal(valeur: Any, nom: str, ligne: int) -> Decimal | None:
    if valeur is None or valeur == "":
        return None
    try:
        resultat = Decimal(str(valeur))
    except (InvalidOperation, ValueError) as erreur:
        raise ValueError(f"Ligne {ligne}: {nom} invalide.") from erreur
    if not resultat.is_finite() or resultat < 0:
        raise ValueError(f"Ligne {ligne}: {nom} doit être positif ou nul.")
    return resultat


def _date(valeur: Any, nom: str, ligne: int) -> date | None:
    if valeur in (None, ""):
        return None
    try:
        return date.fromisoformat(str(valeur))
    except ValueError as erreur:
        raise ValueError(f"Ligne {ligne}: {nom} doit être YYYY-MM-DD.") from erreur


def _datetime(valeur: Any, nom: str, ligne: int) -> datetime | None:
    if valeur in (None, ""):
        return None
    try:
        return datetime.fromisoformat(str(valeur))
    except ValueError as erreur:
        raise ValueError(f"Ligne {ligne}: {nom} doit être ISO-8601.") from erreur
