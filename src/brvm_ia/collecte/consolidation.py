"""Comparaison traçable des observations de marché provenant de plusieurs sources."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class ObservationCours:
    market_bar_id: UUID
    source_code: str
    opening_price: Decimal
    high_price: Decimal | None
    low_price: Decimal | None
    closing_price: Decimal
    volume: Decimal | None


@dataclass(frozen=True, slots=True)
class RapportConsolidation:
    security_id: UUID
    market_date: date
    reference_source: str | None
    status: str
    observations: tuple[ObservationCours, ...]
    divergences: tuple[str, ...]


def comparer_cours(
    session: Session,
    *,
    security_id: UUID,
    market_date: date,
    tolerance_pct: Decimal = Decimal("0.01"),
) -> RapportConsolidation:
    """Compare les cours validés; une source secondaire ne remplace jamais BRVM."""
    rows = session.execute(
        text(
            """
            SELECT mb.market_bar_id, ds.code, mb.opening_price, mb.high_price,
                   mb.low_price, mb.closing_price, mb.volume
            FROM brvm.market_bar AS mb
            JOIN brvm.data_source AS ds ON ds.source_id = mb.source_id
            WHERE mb.security_id = :security_id
              AND mb.market_date = :market_date
              AND mb.validation_status = 'validated'
            ORDER BY (ds.code = 'BRVM') DESC, ds.code
            """
        ),
        {"security_id": security_id, "market_date": market_date},
    ).all()
    observations = tuple(
        ObservationCours(
            market_bar_id=row[0],
            source_code=row[1],
            opening_price=row[2],
            high_price=row[3],
            low_price=row[4],
            closing_price=row[5],
            volume=row[6],
        )
        for row in rows
    )
    if not observations:
        return RapportConsolidation(security_id, market_date, None, "no_observation", (), ())
    reference = next((item for item in observations if item.source_code == "BRVM"), None)
    if reference is None and len(observations) > 1:
        return RapportConsolidation(
            security_id, market_date, None, "no_reference", observations,
            ("Source BRVM absente : aucune source secondaire n'est promue automatiquement.",),
        )
    reference = reference or observations[0]
    divergences: list[str] = []
    for item in observations:
        if item.market_bar_id == reference.market_bar_id:
            continue
        for field in ("opening_price", "high_price", "low_price", "closing_price", "volume"):
            expected = getattr(reference, field)
            actual = getattr(item, field)
            if expected is None or actual is None:
                continue
            if expected == 0:
                different = actual != expected
            else:
                different = abs((actual - expected) / expected) > tolerance_pct
            if different:
                divergences.append(
                    f"{item.source_code}.{field} diverge de BRVM "
                    f"({actual} contre {expected})."
                )
    return RapportConsolidation(
        security_id,
        market_date,
        reference.source_code,
        "divergent" if divergences else "concordant",
        observations,
        tuple(divergences),
    )


def journaliser_divergences(session: Session, rapport: RapportConsolidation) -> int:
    """Crée une anomalie ouverte par observation secondaire divergente."""
    if rapport.status != "divergent":
        return 0
    inserted = 0
    for observation in rapport.observations:
        if observation.source_code == rapport.reference_source:
            continue
        existing = session.execute(
            text(
                """
                SELECT data_quality_issue_id FROM brvm.data_quality_issue
                WHERE market_bar_id = :bar_id AND rule_code = 'multi_source_divergence'
                  AND issue_status = 'open'
                LIMIT 1
                """
            ),
            {"bar_id": observation.market_bar_id},
        ).scalar_one_or_none()
        if existing is not None:
            continue
        session.execute(
            text(
                """
                INSERT INTO brvm.data_quality_issue
                    (market_bar_id, rule_code, severity, description, safe_context)
                VALUES (:bar_id, 'multi_source_divergence', 'warning',
                        'Une observation secondaire diverge de la source BRVM.',
                        CAST(:context AS jsonb))
                """
            ),
            {
                "bar_id": observation.market_bar_id,
                "context": '{"reference_source":"BRVM","secondary_source":"'
                + observation.source_code
                + '"}',
            },
        )
        inserted += 1
    return inserted
