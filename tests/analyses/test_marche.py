"""Tests des résumés de marché avec données synthétiques de test uniquement."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from brvm_ia.analyses.marche import decrire_serie, statistiques_glissantes
from brvm_ia.exceptions import ErreurAnalyse


def test_resume_descriptif_retourne_statistiques_attendues() -> None:
    resume = decrire_serie(pd.Series([1.0, 2.0, 3.0, 4.0]))

    assert resume.nombre_observations == 4
    assert resume.moyenne == pytest.approx(2.5)
    assert resume.mediane == pytest.approx(2.5)
    assert resume.variance == pytest.approx(5 / 3)
    assert resume.ecart_type == pytest.approx(math.sqrt(5 / 3))
    assert resume.quantile_25 == pytest.approx(1.75)
    assert resume.quantile_75 == pytest.approx(3.25)


def test_resume_refuse_serie_trop_courte_et_valeur_non_finie() -> None:
    with pytest.raises(ErreurAnalyse, match="minimum requis = 3"):
        decrire_serie(pd.Series([1.0, 2.0]), minimum_observations=3)
    with pytest.raises(ErreurAnalyse, match="valeur absente ou non finie"):
        decrire_serie(pd.Series([1.0, float("nan")]))


def test_statistiques_glissantes_respectent_la_fenetre() -> None:
    resultats = statistiques_glissantes(pd.Series([2.0, 4.0, 6.0]), fenetre=2)

    assert resultats["moyenne_mobile"].iloc[0] != resultats["moyenne_mobile"].iloc[0]
    assert resultats["moyenne_mobile"].iloc[1] == pytest.approx(3.0)
    assert resultats["moyenne_mobile"].iloc[2] == pytest.approx(5.0)
    assert resultats["ecart_type_mobile"].iloc[1] == pytest.approx(math.sqrt(2.0))


def test_fenetre_invalide_est_refusee() -> None:
    with pytest.raises(ValueError, match="fenetre"):
        statistiques_glissantes(pd.Series([1.0, 2.0]), fenetre=1)
