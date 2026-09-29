"""Statistiques descriptives et temporelles de séries financières fournies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from pandas import Series

from brvm_ia.exceptions import ErreurAnalyse


@dataclass(frozen=True, slots=True)
class StatistiquesDescriptives:
    """Résumé numérique avec écart-type et variance d’échantillon (ddof=1)."""

    nombre_observations: int
    moyenne: float
    mediane: float
    ecart_type: float
    variance: float
    minimum: float
    quantile_25: float
    quantile_75: float
    maximum: float


def decrire_serie(
    valeurs: Series[Any], *, minimum_observations: int = 2
) -> StatistiquesDescriptives:
    """Calcule un résumé descriptif; refuse valeurs manquantes, non finies ou série trop courte."""
    if minimum_observations < 2:
        raise ValueError("minimum_observations doit être supérieur ou égal à 2.")
    numerique = pd.to_numeric(valeurs, errors="coerce").astype("float64")
    if len(numerique) < minimum_observations:
        raise ErreurAnalyse(
            f"Observations insuffisantes; minimum requis = {minimum_observations}, "
            f"observations disponibles = {len(numerique)}."
        )
    if numerique.isna().any() or not np.isfinite(numerique.to_numpy()).all():
        raise ErreurAnalyse("La série contient une valeur absente ou non finie.")
    return StatistiquesDescriptives(
        nombre_observations=len(numerique),
        moyenne=float(numerique.mean()),
        mediane=float(numerique.median()),
        ecart_type=float(numerique.std(ddof=1)),
        variance=float(numerique.var(ddof=1)),
        minimum=float(numerique.min()),
        quantile_25=float(numerique.quantile(0.25)),
        quantile_75=float(numerique.quantile(0.75)),
        maximum=float(numerique.max()),
    )


def statistiques_glissantes(
    valeurs: Series[Any], *, fenetre: int, minimum_observations: int | None = None
) -> pd.DataFrame:
    """Calcule moyenne et volatilité glissantes sans compléter les périodes manquantes."""
    if fenetre < 2:
        raise ValueError("fenetre doit être supérieur ou égal à 2.")
    minimum = fenetre if minimum_observations is None else minimum_observations
    if minimum < 2 or minimum > fenetre:
        raise ValueError("minimum_observations doit être compris entre 2 et fenetre.")
    if isinstance(valeurs.index, pd.DatetimeIndex) and (
        valeurs.index.has_duplicates or not valeurs.index.is_monotonic_increasing
    ):
        raise ErreurAnalyse("L’index temporel doit être unique et trié chronologiquement.")
    numerique = pd.to_numeric(valeurs, errors="coerce").astype("float64")
    if numerique.isna().any() or not np.isfinite(numerique.to_numpy()).all():
        raise ErreurAnalyse("La série contient une valeur absente ou non finie.")
    roule = numerique.rolling(window=fenetre, min_periods=minimum)
    return pd.DataFrame(
        {
            "moyenne_mobile": roule.mean(),
            "ecart_type_mobile": roule.std(ddof=1),
        }
    )
