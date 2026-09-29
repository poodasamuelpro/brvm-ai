"""Tests du moteur de rétro-test sur séries synthétiques réservées aux tests."""

from __future__ import annotations

import pandas as pd
import pytest

from brvm_ia.exceptions import ErreurAnalyse
from brvm_ia.retro_tests.moteur import (
    calculer_metriques_backtest,
    simuler_strategie_longue,
)


def _serie_test() -> tuple[pd.Series[float], pd.Series[float]]:
    dates = pd.date_range("2025-01-01", periods=3, freq="D", tz="UTC")
    cours = pd.Series([100.0, 110.0, 121.0], index=dates)
    signaux = pd.Series([1.0, 0.0, 0.0], index=dates)
    return cours, signaux


def test_signal_est_execute_le_jour_suivant_et_frais_sont_deduits() -> None:
    cours, signaux = _serie_test()

    resultats = simuler_strategie_longue(cours, signaux, frais_points_de_base=10.0)

    assert resultats["position"].tolist() == [0.0, 1.0, 0.0]
    assert resultats["rendement_marche"].tolist() == pytest.approx([0.0, 0.1, 0.1])
    assert resultats["cout_transaction"].tolist() == pytest.approx([0.0, 0.001, 0.001])
    assert resultats["rendement_net"].tolist() == pytest.approx([0.0, 0.099, -0.001])


def test_metriques_composent_les_rendements_et_identifient_les_transitions() -> None:
    cours, signaux = _serie_test()
    resultats = simuler_strategie_longue(cours, signaux, frais_points_de_base=10.0)

    metriques = calculer_metriques_backtest(resultats)

    assert metriques.nombre_periodes == 3
    assert metriques.nombre_transactions == 2
    assert metriques.rendement_total == pytest.approx((1.099 * 0.999) - 1.0)
    assert metriques.volatilite_annualisee is None


def test_signaux_fractionnaires_cours_invalides_et_index_desaligne_sont_refuses() -> None:
    cours, signaux = _serie_test()
    signaux.iloc[0] = 0.5
    with pytest.raises(ErreurAnalyse, match="binaires"):
        simuler_strategie_longue(cours, signaux)

    cours, signaux = _serie_test()
    cours.iloc[1] = 0.0
    with pytest.raises(ErreurAnalyse, match="strictement positifs"):
        simuler_strategie_longue(cours, signaux)

    cours, signaux = _serie_test()
    signaux.index = pd.date_range("2025-01-02", periods=3, freq="D", tz="UTC")
    with pytest.raises(ErreurAnalyse, match="exactement le même index"):
        simuler_strategie_longue(cours, signaux)


def test_index_temporel_invalide_et_frais_negatifs_sont_refuses() -> None:
    cours, signaux = _serie_test()
    cours.index = pd.to_datetime(["2025-01-02", "2025-01-01", "2025-01-03"], utc=True)
    signaux.index = cours.index
    with pytest.raises(ErreurAnalyse, match="trié chronologiquement"):
        simuler_strategie_longue(cours, signaux)

    cours, signaux = _serie_test()
    with pytest.raises(ValueError, match="frais_points_de_base"):
        simuler_strategie_longue(cours, signaux, frais_points_de_base=-1.0)
    resultats = simuler_strategie_longue(cours, signaux)
    with pytest.raises(ValueError, match="periodes_par_an"):
        calculer_metriques_backtest(resultats, periodes_par_an=0)
