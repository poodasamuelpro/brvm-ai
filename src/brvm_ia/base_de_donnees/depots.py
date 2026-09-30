"""Dépôts PostgreSQL en lecture pour les séries et faits financiers validés."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.elements import TextClause

from brvm_ia.base_de_donnees.moteur import GestionnaireBaseDeDonnees
from brvm_ia.exceptions import ErreurBaseDeDonnees, ErreurValidationDonnees


class DepotDonneesPostgres:
    """Charge des observations validées; toutes les valeurs utilisateur sont paramétrées."""

    def __init__(self, gestionnaire: GestionnaireBaseDeDonnees) -> None:
        self._gestionnaire = gestionnaire

    def charger_cours(
        self,
        security_id: UUID,
        date_debut: date,
        date_fin: date,
        interval_code: str,
        as_of: datetime | None = None,
    ) -> pd.DataFrame:
        """Charge les barres validées d’un titre sur une plage inclusive.

        Si `as_of` est fourni, les données non encore collectées à cet instant et
        celles publiées après sont exclues pour limiter l’anticipation temporelle.
        """
        self._valider_plage(date_debut, date_fin, as_of)
        if not interval_code or interval_code != interval_code.strip().lower():
            raise ErreurValidationDonnees("interval_code doit être non vide et en minuscules.")

        requete = text(
            """
            SELECT market_date, period_start, period_end, opening_price, high_price,
                   low_price, closing_price, adjusted_close, adjustment_method,
                   volume, traded_value, trade_count, source_id, published_at, collected_at
            FROM brvm.market_bar
            WHERE security_id = :security_id
              AND interval_code = :interval_code
              AND market_date BETWEEN :date_debut AND :date_fin
              AND validation_status = 'validated'
              AND (
                    :as_of IS NULL
                    OR (
                        collected_at <= :as_of
                        AND (published_at IS NULL OR published_at <= :as_of)
                    )
              )
            ORDER BY period_start ASC
            """
        )
        return self._lire(
            requete,
            {
                "security_id": security_id,
                "interval_code": interval_code,
                "date_debut": date_debut,
                "date_fin": date_fin,
                "as_of": as_of,
            },
            "cours",
        )

    def charger_faits_fondamentaux(
        self,
        company_id: UUID,
        date_debut: date,
        date_fin: date,
        as_of: datetime | None = None,
    ) -> pd.DataFrame:
        """Charge les faits publiés d’une société, dans les périodes demandées.

        En mode `as_of`, les faits sans `available_at` connu sont volontairement
        exclus : aucune date de publication/disponibilité n’est inventée.
        """
        self._valider_plage(date_debut, date_fin, as_of)
        requete = text(
            """
            SELECT p.period_start, p.period_end, p.period_kind, p.reporting_scope,
                   f.metric_code, f.value, f.currency_code, f.unit_code,
                   f.published_at, f.available_at, f.collected_at, f.source_id
            FROM brvm.financial_fact AS f
            JOIN brvm.financial_period AS p
              ON p.financial_period_id = f.financial_period_id
            WHERE p.company_id = :company_id
              AND p.period_end BETWEEN :date_debut AND :date_fin
              AND f.validation_status = 'validated'
              AND (
                    :as_of IS NULL
                    OR (
                        f.available_at IS NOT NULL
                        AND f.available_at <= :as_of
                        AND f.collected_at <= :as_of
                        AND (f.published_at IS NULL OR f.published_at <= :as_of)
                    )
              )
            ORDER BY p.period_end ASC, f.metric_code ASC
            """
        )
        return self._lire(
            requete,
            {
                "company_id": company_id,
                "date_debut": date_debut,
                "date_fin": date_fin,
                "as_of": as_of,
            },
            "faits fondamentaux",
        )

    def _lire(
        self,
        requete: TextClause,
        parametres: dict[str, Any],
        nature: str,
    ) -> pd.DataFrame:
        try:
            with self._gestionnaire.moteur.connect() as connexion:
                return pd.read_sql_query(requete, connexion, params=parametres)
        except (SQLAlchemyError, pd.errors.DatabaseError):
            raise ErreurBaseDeDonnees(
                f"Lecture des {nature} impossible; l’URL et les valeurs sensibles sont masquées."
            ) from None

    @staticmethod
    def _valider_plage(
        date_debut: date,
        date_fin: date,
        as_of: datetime | None,
    ) -> None:
        if date_fin < date_debut:
            raise ErreurValidationDonnees("date_fin doit être supérieure ou égale à date_debut.")
        if as_of is not None and (as_of.tzinfo is None or as_of.utcoffset() is None):
            raise ErreurValidationDonnees("as_of doit inclure un fuseau horaire.")
