"""Tests de validation sur de petits cas synthétiques, jamais présentés comme données BRVM."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest

from brvm_ia.exceptions import ErreurValidationDonnees
from brvm_ia.nettoyage.validation import (
    exiger_donnees_marche_valides,
    valider_donnees_marche,
)


def _donnees_marche() -> pd.DataFrame:
    """Jeu de test synthétique et contrôlé."""
    return pd.DataFrame(
        {
            "date": ["2025-01-02T00:00:00Z", "2025-01-03T00:00:00Z"],
            "entreprise": ["Société test", "Société test"],
            "ticker": ["TEST", "TEST"],
            "ouverture": [10.0, 11.0],
            "plus_haut": [12.0, 13.0],
            "plus_bas": [9.0, 10.5],
            "cloture": [11.0, 12.0],
            "volume": [1000, 1200],
        }
    )


def test_lot_ohlcv_coherent_est_valide_sans_modifier_la_source() -> None:
    donnees = _donnees_marche()
    donnees.index = [10, 20]
    original = donnees.copy(deep=True)
    rapport = valider_donnees_marche(
        donnees,
        date_reference=datetime(2025, 2, 1, tzinfo=UTC),
    )

    assert rapport.est_valide
    assert rapport.nombre_lignes == 2
    assert not rapport.anomalies
    pd.testing.assert_frame_equal(donnees, original)


def test_colonne_manquante_est_identifiee() -> None:
    donnees = _donnees_marche().drop(columns="volume")

    rapport = valider_donnees_marche(donnees)

    assert not rapport.est_valide
    assert [(a.code, a.colonne) for a in rapport.erreurs] == [("colonne_absente", "volume")]


def test_prix_volume_et_ordre_ohlc_invalides_sont_signales() -> None:
    donnees = _donnees_marche()
    donnees.loc[0, "ouverture"] = 0
    donnees.loc[0, "volume"] = -5
    donnees.loc[1, "plus_haut"] = 10

    rapport = valider_donnees_marche(donnees)

    codes = {anomalie.code for anomalie in rapport.erreurs}
    assert {"prix_non_positif", "volume_negatif", "ordre_ohlc_incoherent"} <= codes


def test_dates_futures_invalides_et_doublons_sont_distincts() -> None:
    donnees = _donnees_marche()
    donnees.loc[1, "date"] = donnees.loc[0, "date"]
    donnees.loc[1, "ticker"] = donnees.loc[0, "ticker"]

    rapport = valider_donnees_marche(
        donnees,
        date_reference=datetime(2025, 1, 2, 12, tzinfo=UTC),
    )

    codes = {anomalie.code for anomalie in rapport.erreurs}
    assert "doublon_temporel" in codes
    assert "date_future" not in codes

    donnees.loc[1, "date"] = "2025-01-04T00:00:00Z"
    rapport = valider_donnees_marche(
        donnees,
        date_reference=datetime(2025, 1, 3, tzinfo=UTC),
    )
    assert "date_future" in {anomalie.code for anomalie in rapport.erreurs}


def test_date_invalide_ticker_vide_et_valeur_manquante_sont_signales() -> None:
    donnees = _donnees_marche()
    donnees.loc[0, "date"] = "pas-une-date"
    donnees.loc[0, "ticker"] = "  "
    donnees.loc[1, "cloture"] = None

    rapport = valider_donnees_marche(donnees)

    codes = {anomalie.code for anomalie in rapport.erreurs}
    assert {"date_invalide", "ticker_invalide", "valeur_absente"} <= codes
    with pytest.raises(ErreurValidationDonnees, match="Lot OHLCV invalide"):
        exiger_donnees_marche_valides(rapport)


def test_variation_extreme_est_alertee_sans_rejeter_le_lot() -> None:
    donnees = _donnees_marche()
    donnees.loc[1, "cloture"] = 15.0
    donnees.loc[1, "plus_haut"] = 16.0

    rapport = valider_donnees_marche(
        donnees,
        date_reference=datetime(2025, 2, 1, tzinfo=UTC),
        seuil_alerte_variation_absolue=0.2,
    )

    assert rapport.est_valide
    assert len(rapport.avertissements) == 1
    assert rapport.avertissements[0].code == "variation_extreme"


def test_frequence_est_comparee_a_un_calendrier_fourni_sans_le_deviner() -> None:
    donnees = _donnees_marche()
    donnees.loc[1, "date"] = "2025-01-04T00:00:00Z"
    calendrier = [
        datetime(2025, 1, 2, tzinfo=UTC),
        datetime(2025, 1, 3, tzinfo=UTC),
        datetime(2025, 1, 4, tzinfo=UTC),
    ]

    rapport = valider_donnees_marche(
        donnees,
        date_reference=datetime(2025, 2, 1, tzinfo=UTC),
        dates_attendues=calendrier,
    )

    assert rapport.est_valide
    assert len(rapport.avertissements) == 1
    assert rapport.avertissements[0].code == "cotation_attendue_absente"


def test_seuil_variation_non_positif_est_refuse() -> None:
    with pytest.raises(ValueError, match="strictement positif"):
        valider_donnees_marche(_donnees_marche(), seuil_alerte_variation_absolue=0)
