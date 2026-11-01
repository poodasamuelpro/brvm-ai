"""Validation et persistance de faits financiers publiés."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class FaitFinancier:
    security_symbol: str
    period_start: date
    period_end: date
    period_kind: str
    reporting_scope: str
    metric_code: str
    value: Decimal
    unit_code: str
    currency_code: str | None = None
    published_at: datetime | None = None
    available_at: datetime | None = None
    validation_status: str = "pending"


def lire_faits(payload: list[dict[str, Any]]) -> tuple[FaitFinancier, ...]:
    resultat: list[FaitFinancier] = []
    for index, ligne in enumerate(payload, start=1):
        status = str(ligne.get("validation_status", "pending")).strip().lower()
        if status not in {"pending", "validated", "rejected", "quarantined"}:
            raise ValueError(f"Ligne {index}: validation_status invalide.")
        resultat.append(
            FaitFinancier(
                security_symbol=_required_text(ligne.get("security_symbol"), "security_symbol", index),
                period_start=_required_date(ligne.get("period_start"), "period_start", index),
                period_end=_required_date(ligne.get("period_end"), "period_end", index),
                period_kind=_required_text(ligne.get("period_kind"), "period_kind", index).lower(),
                reporting_scope=_required_text(ligne.get("reporting_scope"), "reporting_scope", index).lower(),
                metric_code=_required_text(ligne.get("metric_code"), "metric_code", index).lower(),
                value=_required_decimal(ligne.get("value"), "value", index),
                unit_code=_required_text(ligne.get("unit_code"), "unit_code", index).lower(),
                currency_code=_optional_text(ligne.get("currency_code"), index, upper=True),
                published_at=_optional_datetime(ligne.get("published_at"), "published_at", index),
                available_at=_optional_datetime(ligne.get("available_at"), "available_at", index),
                validation_status=status,
            )
        )
    return tuple(resultat)


def enregistrer_faits(
    session: Session,
    *,
    source_id: UUID,
    raw_ingest_record_id: UUID,
    faits: tuple[FaitFinancier, ...],
) -> int:
    inseres = 0
    for fait in faits:
        company_id = session.execute(
            text(
                """
                SELECT s.company_id
                FROM brvm.security_symbol_history AS h
                JOIN brvm.security AS s ON s.security_id = h.security_id
                WHERE h.symbol = :symbol
                  AND h.valid_from <= :period_end
                  AND (h.valid_to IS NULL OR h.valid_to >= :period_start)
                ORDER BY h.valid_from DESC
                LIMIT 1
                """
            ),
            {"symbol": fait.security_symbol, "period_start": fait.period_start, "period_end": fait.period_end},
        ).scalar_one_or_none()
        if company_id is None:
            raise ValueError(f"Symbole BRVM non résolu : {fait.security_symbol}.")

        period_id = session.execute(
            text(
                """
                INSERT INTO brvm.financial_period
                    (company_id, period_start, period_end, period_kind, reporting_scope)
                VALUES (:company_id, :period_start, :period_end, :period_kind, :scope)
                ON CONFLICT (company_id, period_start, period_end, period_kind, reporting_scope)
                DO UPDATE SET reporting_scope = EXCLUDED.reporting_scope
                RETURNING financial_period_id
                """
            ),
            {
                "company_id": company_id,
                "period_start": fait.period_start,
                "period_end": fait.period_end,
                "period_kind": fait.period_kind,
                "scope": fait.reporting_scope,
            },
        ).scalar_one()
        existing = session.execute(
            text(
                """
                SELECT financial_fact_id FROM brvm.financial_fact
                WHERE raw_ingest_record_id = :raw_id
                  AND financial_period_id = :period_id
                  AND metric_code = :metric_code
                  AND unit_code = :unit_code
                LIMIT 1
                """
            ),
            {
                "raw_id": raw_ingest_record_id,
                "period_id": period_id,
                "metric_code": fait.metric_code,
                "unit_code": fait.unit_code,
            },
        ).scalar_one_or_none()
        if existing is not None:
            continue
        session.execute(
            text(
                """
                INSERT INTO brvm.financial_fact
                    (financial_period_id, source_id, raw_ingest_record_id, metric_code,
                     value, currency_code, unit_code, published_at, available_at, validation_status)
                VALUES (:period_id, :source_id, :raw_id, :metric_code,
                        :value, :currency, :unit_code, :published_at, :available_at, :status)
                """
            ),
            {
                "period_id": period_id,
                "source_id": source_id,
                "raw_id": raw_ingest_record_id,
                "metric_code": fait.metric_code,
                "value": fait.value,
                "currency": fait.currency_code,
                "unit_code": fait.unit_code,
                "published_at": fait.published_at,
                "available_at": fait.available_at,
                "status": fait.validation_status,
            },
        )
        inseres += 1
    return inseres


def _required_text(value: Any, name: str, line: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Ligne {line}: {name} requis.")
    return value.strip()


def _optional_text(value: Any, line: int, *, upper: bool = False) -> str | None:
    if value in (None, ""):
        return None
    result = _required_text(value, "currency_code", line)
    return result.upper() if upper else result


def _required_date(value: Any, name: str, line: int) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as error:
        raise ValueError(f"Ligne {line}: {name} doit être YYYY-MM-DD.") from error


def _required_decimal(value: Any, name: str, line: int) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"Ligne {line}: {name} invalide.") from error
    if not result.is_finite():
        raise ValueError(f"Ligne {line}: {name} non fini.")
    return result


def _optional_datetime(value: Any, name: str, line: int) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError as error:
        raise ValueError(f"Ligne {line}: {name} doit être ISO-8601.") from error
