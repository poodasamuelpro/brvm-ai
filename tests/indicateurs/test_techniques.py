"""Tests numériques de fonctions financières déterministes sur fixtures synthétiques."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from brvm_ia.exceptions import ErreurAnalyse
from brvm_ia.indicateurs.techniques import (
    drawdown_maximal,
    rendement_cumule,
    rendements_logarithmiques,
    rendements_simples,
    volatilite_annualisee,
)


def test_rendements_simples_logarithmiques_et_composes() -> None:
    clotures = pd.Series([100.0, 110.0, 99.0])

    simples = rendements_simples(clotures)
    logarithmiques = rendements_logarithmiques(clotures)

    np.testing.assert_allclose(simples.to_numpy(), [0.1, -0.1])
    np.testing.assert_allclose(logarithmiques.to_numpy(), np.log([1.1, 0.9]))
    assert rendement_cumule(simples) == pytest.approx(-0.01)


def test_drawdown_inclut_le_niveau_de_richesse_initial() -> None:
    rendements = pd.Series([-0.1, 0.05, -0.2])

    assert drawdown_maximal(rendements) == pytest.approx(-0.244)


def test_volatilite_utilise_ecart_type_echantillonnal_et_facteur_annuel() -> None:
    rendements = pd.Series([0.01, 0.02] * 10)
    attendue = float(rendements.std(ddof=1) * math.sqrt(252))

    assert volatilite_annualisee(rendements) == pytest.approx(attendue)


def test_serie_datee_non_chronologique_est_refusee() -> None:
    clotures = pd.Series(
        [100.0, 110.0],
        index=pd.to_datetime(["2025-01-03", "2025-01-02"], utc=True),
    )

    with pytest.raises(ErreurAnalyse, match="trié chronologiquement"):
        rendements_simples(clotures)


def test_fonctions_refusent_donnees_insuffisantes_ou_impossibles() -> None:
    with pytest.raises(ErreurAnalyse, match="minimum requis = 2"):
        rendements_simples(pd.Series([100.0]))
    with pytest.raises(ErreurAnalyse, match="strictement positifs"):
        rendements_simples(pd.Series([100.0, 0.0]))
    with pytest.raises(ErreurAnalyse, match="inférieur à -100 %"):
        rendement_cumule(pd.Series([-1.01]))
    with pytest.raises(ErreurAnalyse, match="minimum requis = 20"):
        volatilite_annualisee(pd.Series([0.01, 0.02]))
