"""Moteur de backtest prix-only, long-only et exécuté après émission du signal."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from pandas import Series

from brvm_ia.exceptions import ErreurAnalyse
from brvm_ia.indicateurs.techniques import (
    drawdown_maximal,
    rendement_cumule,
    volatilite_annualisee,
)

ColonnesResultat = (
    "position",
    "rendement_marche",
    "cout_transaction",
    "rendement_net",
    "indice_cumule",
)


def simuler_strategie_longue(
    cours_de_cloture: Series[Any],
    signaux: Series[Any],
    *,
    frais_points_de_base: float = 0.0,
) -> pd.DataFrame:
    """Simule des positions longues 0/1, avec exécution au cours de clôture suivant.

    Les signaux horodatés à la clôture ``t`` ne peuvent affecter le rendement
    qu’à partir de ``t+1``. Les frais sont facturés sur toute variation de position,
    à l’entrée comme à la sortie. Les dividendes et le slippage ne sont pas modélisés.
    """
    if not isinstance(cours_de_cloture, pd.Series) or not isinstance(signaux, pd.Series):
        raise TypeError("cours_de_cloture et signaux doivent être des pandas.Series.")
    if not math.isfinite(frais_points_de_base) or frais_points_de_base < 0:
        raise ValueError("frais_points_de_base doit être fini et positif ou nul.")
    index = cours_de_cloture.index
    if not isinstance(index, pd.DatetimeIndex):
        raise ErreurAnalyse("Le backtest requiert un index de dates explicite.")
    if index.has_duplicates or not index.is_monotonic_increasing:
        raise ErreurAnalyse("L’index temporel doit être unique et trié chronologiquement.")
    if not index.equals(signaux.index):
        raise ErreurAnalyse("Les signaux et les cours doivent avoir exactement le même index.")
    if len(cours_de_cloture) < 2:
        raise ErreurAnalyse("Le backtest exige au moins deux observations de cours.")

    cours = pd.to_numeric(cours_de_cloture, errors="coerce").astype("float64")
    signal = pd.to_numeric(signaux, errors="coerce").astype("float64")
    if cours.isna().any() or not np.isfinite(cours.to_numpy()).all() or cours.le(0).any():
        raise ErreurAnalyse("Les cours doivent être présents, finis et strictement positifs.")
    if signal.isna().any() or not np.isfinite(signal.to_numpy()).all():
        raise ErreurAnalyse("Les signaux doivent être présents et finis.")
    if not signal.isin([0.0, 1.0]).all():
        raise ErreurAnalyse("Les signaux doivent être binaires: 0 (hors marché) ou 1 (long).")

    positions = signal.shift(1, fill_value=0.0)
    rendements_marche = cours.pct_change(fill_method=None).fillna(0.0)
    changements = positions.diff().abs().fillna(0.0)
    couts = changements * (frais_points_de_base / 10_000.0)
    rendements_nets = positions * rendements_marche - couts
    if not np.isfinite(rendements_nets.to_numpy()).all() or rendements_nets.le(-1.0).any():
        raise ErreurAnalyse("Les frais ou rendements impliquent une perte quotidienne impossible.")
    indice = (1.0 + rendements_nets).cumprod()
    if not np.isfinite(indice.to_numpy()).all():
        raise ErreurAnalyse("La courbe patrimoniale du backtest déborde les limites numériques.")

    return pd.DataFrame(
        {
            "position": positions,
            "rendement_marche": rendements_marche,
            "cout_transaction": couts,
            "rendement_net": rendements_nets,
            "indice_cumule": indice,
        },
        index=index,
    )


@dataclass(frozen=True, slots=True)
class MetriquesBacktest:
    """Résumé net des coûts; la volatilité reste absente si l’échantillon est trop court."""

    nombre_periodes: int
    nombre_transactions: int
    rendement_total: float
    drawdown_maximal: float
    volatilite_annualisee: float | None


def calculer_metriques_backtest(
    resultats: pd.DataFrame,
    *,
    periodes_par_an: int = 252,
    minimum_observations_volatilite: int = 20,
) -> MetriquesBacktest:
    """Calcule les métriques du moteur et n’affiche pas une volatilité sous-échantillonnée."""
    if periodes_par_an < 1:
        raise ValueError("periodes_par_an doit être supérieur ou égal à 1.")
    if minimum_observations_volatilite < 2:
        raise ValueError("minimum_observations_volatilite doit être supérieur ou égal à 2.")
    manquantes = [colonne for colonne in ColonnesResultat if colonne not in resultats.columns]
    if manquantes:
        raise ErreurAnalyse("Résultats de backtest incomplets: " + ", ".join(manquantes))
    rendements = pd.to_numeric(resultats["rendement_net"], errors="coerce").astype("float64")
    positions = pd.to_numeric(resultats["position"], errors="coerce").astype("float64")
    nombre = len(resultats)
    if nombre == 0:
        raise ErreurAnalyse("Aucune période à résumer dans le backtest.")
    if (
        rendements.isna().any()
        or not np.isfinite(rendements.to_numpy()).all()
        or rendements.le(-1.0).any()
    ):
        raise ErreurAnalyse("Les rendements nets du backtest sont incomplets ou impossibles.")
    if positions.isna().any() or not positions.isin([0.0, 1.0]).all():
        raise ErreurAnalyse("Les positions du backtest doivent être binaires et présentes.")
    changements = positions.diff().abs().fillna(0.0)
    transactions = int(changements.gt(0).sum())
    vol = (
        volatilite_annualisee(
            rendements,
            periodes_par_an=periodes_par_an,
            minimum_observations=minimum_observations_volatilite,
        )
        if nombre >= minimum_observations_volatilite
        else None
    )
    return MetriquesBacktest(
        nombre_periodes=nombre,
        nombre_transactions=transactions,
        rendement_total=rendement_cumule(rendements),
        drawdown_maximal=drawdown_maximal(rendements),
        volatilite_annualisee=vol,
    )
