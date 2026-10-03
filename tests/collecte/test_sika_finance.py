from datetime import date
from decimal import Decimal

import pytest

from brvm_ia.collecte.sources.sika_finance import analyser_reponse
from brvm_ia.exceptions import ErreurValidationDonnees


def ligne(date_: str = "02/10/2026") -> dict[str, str]:
    return {
        "date": date_,
        "open": "45 000",
        "high": "45 000",
        "low": "44 900",
        "close": "45 000",
        "volume": "36 615",
        "value": "1 647 675 000",
        "variation": "0,00",
    }


def test_analyse_une_ligne_sika():
    resultat = analyser_reponse([ligne()], "SNTS.sn")
    assert len(resultat) == 1
    assert resultat[0].ticker_sika == "SNTS.sn"
    assert resultat[0].date_seance == date(2026, 10, 2)
    assert resultat[0].cloture == Decimal("45000")
    assert resultat[0].volume_titres == Decimal("36615")
    assert resultat[0].volume_fcfa == Decimal("1647675000")


def test_analyse_refuse_ohlc_incoherent():
    mauvaise = ligne()
    mauvaise["low"] = "46 000"
    with pytest.raises(ErreurValidationDonnees, match="OHLC incohérent"):
        analyser_reponse([mauvaise], "SNTS.sn")


def test_analyse_refuse_doublon():
    with pytest.raises(ErreurValidationDonnees, match="Doublon"):
        analyser_reponse([ligne(), ligne()], "SNTS.sn")


def test_analyse_accepte_enveloppe_data():
    resultat = analyser_reponse({"data": [ligne("01/10/2026")]}, "SNTS.sn")
    assert resultat[0].date_seance == date(2026, 10, 1)
