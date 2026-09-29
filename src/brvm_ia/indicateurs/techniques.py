"""Indicateurs de marché calculés sur séries réellement fournies par l’appelant."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from pandas import Series

from brvm_ia.exceptions import ErreurAnalyse


def _valider_serie(valeurs: Series[Any], *, minimum: int, nom: str) -> Series[float]:
    if not isinstance(valeurs, pd.Series):
        raise TypeError(f"{nom} doit être une pandas.Series.")
    if isinstance(valeurs.index, pd.DatetimeIndex) and (
        valeurs.index.has_duplicates or not valeurs.index.is_monotonic_increasing
    ):
        raise ErreurAnalyse("L’index temporel doit être unique et trié chronologiquement.")
    numerique = pd.to_numeric(valeurs, errors="coerce").astype("float64")
    if len(numerique) < minimum:
        raise ErreurAnalyse(
            f"{nom}: observations insuffisantes; minimum requis = {minimum}, "
            f"observations disponibles = {len(numerique)}."
        )
    if numerique.isna().any() or not np.isfinite(numerique.to_numpy()).all():
        raise ErreurAnalyse(f"{nom} contient une valeur absente ou non finie.")
    return numerique


def rendements_simples(cours_de_cloture: Series[Any]) -> Series[float]:
    """Calcule les rendements simples successifs de cours strictement positifs."""
    cours = _valider_serie(cours_de_cloture, minimum=2, nom="Cours de clôture")
    if cours.le(0).any():
        raise ErreurAnalyse("Les cours de clôture doivent être strictement positifs.")
    rendements = cours.pct_change(fill_method=None).iloc[1:]
    rendements.name = "rendement_simple"
    return rendements


def rendements_logarithmiques(cours_de_cloture: Series[Any]) -> Series[float]:
    """Calcule ln(P[t]/P[t-1]); refuse les prix nuls, négatifs ou non finis."""
    cours = _valider_serie(cours_de_cloture, minimum=2, nom="Cours de clôture")
    if cours.le(0).any():
        raise ErreurAnalyse("Les cours de clôture doivent être strictement positifs.")
    logarithmes = np.log(cours / cours.shift(1))
    rendements = pd.Series(logarithmes, index=cours.index, dtype="float64").iloc[1:]
    rendements.name = "rendement_logarithmique"
    return rendements


def rendement_cumule(rendements: Series[Any]) -> float:
    """Compose des rendements par multiplication, sans les additionner."""
    serie = _valider_serie(rendements, minimum=1, nom="Rendements")
    if serie.lt(-1).any():
        raise ErreurAnalyse("Un rendement inférieur à -100 % est impossible.")
    resultat = float(np.prod(1.0 + serie.to_numpy()) - 1.0)
    if not math.isfinite(resultat):
        raise ErreurAnalyse("Le rendement cumulé n’est pas fini.")
    return resultat


def volatilite_annualisee(
    rendements: Series[Any],
    *,
    periodes_par_an: int = 252,
    minimum_observations: int = 20,
) -> float:
    """Écart-type échantillonnal des rendements mis à l’échelle par √périodes/an."""
    if periodes_par_an < 1:
        raise ValueError("periodes_par_an doit être supérieur ou égal à 1.")
    if minimum_observations < 2:
        raise ValueError("minimum_observations doit être supérieur ou égal à 2.")
    serie = _valider_serie(rendements, minimum=minimum_observations, nom="Rendements")
    if serie.le(-1).any():
        raise ErreurAnalyse("Les rendements doivent être supérieurs à -100 %.")
    return float(serie.std(ddof=1) * math.sqrt(periodes_par_an))


def drawdown_maximal(rendements: Series[Any]) -> float:
    """Retourne le drawdown maximal (valeur nulle ou négative), avec NAV initiale à 1."""
    serie = _valider_serie(rendements, minimum=1, nom="Rendements")
    if serie.lt(-1).any():
        raise ErreurAnalyse("Un rendement inférieur à -100 % est impossible.")
    richesse = (1.0 + serie).cumprod().reset_index(drop=True)
    richesse = pd.concat([pd.Series([1.0]), richesse], ignore_index=True)
    drawdowns = richesse.div(richesse.cummax()).sub(1.0)
    return float(drawdowns.min())
