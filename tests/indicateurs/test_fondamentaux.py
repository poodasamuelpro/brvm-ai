"""Tests des ratios sur données synthétiques de test, et non sur des sociétés BRVM réelles."""

from __future__ import annotations

import math

import pytest

from brvm_ia.indicateurs.fondamentaux import (
    DonneesFondamentales,
    calculer_croissance,
    calculer_ratios_fondamentaux,
)


def test_ratios_fondamentaux_sont_calcules_avec_les_bons_denominateurs() -> None:
    donnees = DonneesFondamentales(
        chiffre_affaires=200.0,
        resultat_net=20.0,
        capitaux_propres=100.0,
        actifs=200.0,
        passifs=60.0,
        dividende_par_action=2.0,
        benefice_par_action=4.0,
        cours_action=40.0,
    )

    ratios = calculer_ratios_fondamentaux(donnees)

    assert ratios.marge_nette == pytest.approx(0.1)
    assert ratios.rentabilite_capitaux_propres == pytest.approx(0.2)
    assert ratios.rentabilite_actifs == pytest.approx(0.1)
    assert ratios.ratio_passifs_actifs == pytest.approx(0.3)
    assert ratios.rendement_dividende == pytest.approx(0.05)
    assert ratios.ratio_cours_benefice == pytest.approx(10.0)


def test_donnees_absentes_et_ratios_indefinis_ne_sont_pas_imputes() -> None:
    ratios = calculer_ratios_fondamentaux(
        DonneesFondamentales(chiffre_affaires=0.0, resultat_net=10.0, actifs=0.0)
    )

    assert ratios.marge_nette is None
    assert ratios.rentabilite_actifs is None
    assert ratios.ratio_passifs_actifs is None
    assert ratios.rentabilite_capitaux_propres is None
    assert ratios.ratio_cours_benefice is None


def test_per_est_indisponible_pour_benefice_par_action_nul_ou_negatif() -> None:
    ratios = calculer_ratios_fondamentaux(
        DonneesFondamentales(cours_action=100.0, benefice_par_action=-2.0)
    )

    assert ratios.ratio_cours_benefice is None


def test_donnees_financieres_non_finies_ou_negatives_sont_refusees() -> None:
    with pytest.raises(ValueError, match="finie"):
        DonneesFondamentales(resultat_net=math.inf)
    with pytest.raises(ValueError, match="ne peut pas être négatif"):
        DonneesFondamentales(actifs=-1.0)
    with pytest.raises(ValueError, match="strictement positif"):
        DonneesFondamentales(cours_action=0.0)
    with pytest.raises(ValueError, match="valeur numérique finie"):
        DonneesFondamentales(resultat_net="inconnu")  # type: ignore[arg-type]


def test_croissance_respecte_periode_de_base_absente_ou_nulle() -> None:
    assert calculer_croissance(110.0, 100.0) == pytest.approx(0.1)
    assert calculer_croissance(10.0, 0.0) is None
    assert calculer_croissance(None, 5.0) is None
