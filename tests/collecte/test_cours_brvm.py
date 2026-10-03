"""Analyse et validation de la page BRVM « Cours des actions », hors ligne.

Le HTML ci-dessous reprend la structure et trois lignes réellement publiées sur
https://www.brvm.org/fr/cours-actions/0 (mise à jour du 2 octobre 2026 - 22:45),
réduites au strict nécessaire. Les cas d’erreur sont des variantes explicites.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from brvm_ia.collecte.sources.donnees_marche import analyser_page_cours_actions
from brvm_ia.collecte.validateurs import convertir_nombre_fr, valider_page
from brvm_ia.exceptions import ErreurCollecte, ErreurValidationDonnees

_ENTETE = (
    "<tr><th>Symbole</th><th>Nom</th><th>Volume</th><th>Cours veille (FCFA)</th>"
    "<th>Cours Ouverture (FCFA)</th><th>Cours Clôture (FCFA)</th><th>Variation (%)</th></tr>"
)
_LIGNES = (
    "<tr><td>ABJC</td><td>SERVAIR ABIDJAN  COTE D'IVOIRE</td><td>4 711</td><td>3 500</td>"
    "<td>3 370</td><td>3 500</td><td><span>3,86</span></td></tr>"
    "<tr><td>SEMC</td><td>EVIOSYS PACKAGING SIEM COTE D'IVOIRE</td><td>0</td><td>1 495</td>"
    "<td>0</td><td>1 495</td><td><span>0,00</span></td></tr>"
    "<tr><td>SNTS</td><td>SONATEL SENEGAL</td><td>36 615</td><td>45 000</td>"
    "<td>45 000</td><td>45 000</td><td><span>0,00</span></td></tr>"
)
_MAINTENANT = datetime(2026, 10, 3, 1, 30, tzinfo=UTC)


def _html(lignes: str = _LIGNES, fermee: bool = True) -> str:
    seance = '<div class="seance-fermee">Séance fermée</div>' if fermee else ""
    return (
        f"<html><body>{seance}<section>Dernière mise à jour : Vendredi, 2 octobre, 2026 - 22:45"
        f"</section><table><thead>{_ENTETE}</thead><tbody>{lignes}</tbody></table></body></html>"
    )


def test_page_reelle_est_analysee_et_normalisee() -> None:
    page = analyser_page_cours_actions(_html())
    assert page.seance_fermee
    assert page.mise_a_jour_source.isoformat() == "2026-10-02T22:45:00+00:00"
    date_seance, resultats = valider_page(page, _MAINTENANT)
    assert date_seance == date(2026, 10, 2)
    assert [r.est_rejetee for r in resultats] == [False, False, False]
    abjc = resultats[0].cours
    assert abjc is not None
    assert (abjc.ouverture, abjc.cloture, abjc.volume) == (
        Decimal("3370"),
        Decimal("3500"),
        Decimal("4711"),
    )


def test_volume_nul_ne_stocke_pas_une_ouverture_a_zero() -> None:
    _, resultats = valider_page(analyser_page_cours_actions(_html()), _MAINTENANT)
    semc = resultats[1]
    assert semc.cours is not None and semc.cours.ouverture is None
    assert any(c.regle == "aucune_transaction" for c in semc.constats)


def test_seance_ouverte_est_refusee() -> None:
    page = analyser_page_cours_actions(_html(fermee=False))
    with pytest.raises(ErreurValidationDonnees, match="non fermée"):
        valider_page(page, _MAINTENANT)


def test_structure_modifiee_echoue_explicitement() -> None:
    with pytest.raises(ErreurCollecte, match="introuvable"):
        analyser_page_cours_actions(_html().replace("Cours Clôture (FCFA)", "Dernier"))


def test_valeurs_invalides_et_doublons_sont_rejetes() -> None:
    lignes = (
        _LIGNES + "<tr><td>SNTS</td><td>SONATEL SENEGAL</td><td>1</td><td>1</td><td>1</td>"
        "<td>1</td><td>0,00</td></tr>"
        "<tr><td>XXXX</td><td>TITRE</td><td>n/d</td><td>1</td><td>1</td><td>1</td>"
        "<td>0</td></tr>"
    )
    _, resultats = valider_page(analyser_page_cours_actions(_html(lignes)), _MAINTENANT)
    regles = [{c.regle for c in r.constats} for r in resultats if r.est_rejetee]
    assert len(regles) == 3
    assert sum("symbole_duplique" in r for r in regles) == 2
    assert any("nombre_invalide" in r for r in regles)


def test_conversion_nombre_francais() -> None:
    assert convertir_nombre_fr("21 441 961") == Decimal("21441961")
    assert convertir_nombre_fr("-0,35") == Decimal("-0.35")
    with pytest.raises(ErreurValidationDonnees):
        convertir_nombre_fr("3,86%")
