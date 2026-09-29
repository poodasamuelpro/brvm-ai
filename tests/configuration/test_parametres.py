"""Tests des paramètres; aucune vraie clé ni connexion n’est utilisée."""

from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest
from pydantic import ValidationError

from brvm_ia.configuration.parametres import (
    Parametres,
    charger_parametres,
    obtenir_parametres,
)
from brvm_ia.exceptions import ErreurConfiguration
from brvm_ia.journalisation import configurer_journalisation


@pytest.fixture(autouse=True)
def nettoyer_cache() -> Iterator[None]:
    """Évite qu’un test réutilise les paramètres mis en cache par un autre."""
    obtenir_parametres.cache_clear()
    yield
    obtenir_parametres.cache_clear()


def test_parametres_par_defaut_desactivent_les_integrations() -> None:
    parametres = Parametres(_env_file=None)

    assert parametres.environnement == "developpement"
    assert parametres.email_port == 587
    assert parametres.fuseau_horaire == "Africa/Abidjan"
    assert not parametres.activer_base_de_donnees
    assert not parametres.activer_telegram
    assert parametres.telegram_bot_token is None


def test_valeurs_env_valides_sont_chargees(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONNEMENT", "test")
    monkeypatch.setenv("FREQUENCE_COLLECTE_MINUTES", "60")

    parametres = charger_parametres()

    assert parametres.environnement == "test"
    assert parametres.frequence_collecte_minutes == 60


def test_environnement_inconnu_est_rejete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONNEMENT", "staging")

    with pytest.raises(ErreurConfiguration, match="ENVIRONNEMENT"):
        charger_parametres()


def test_integration_desactivee_ne_requiert_pas_de_secrets() -> None:
    parametres = Parametres(_env_file=None)

    assert parametres.telegram_bot_token is None
    assert parametres.cle_api_ia is None
    assert parametres.base_de_donnees_url is None


def test_telegram_actif_exige_token_et_chat_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ACTIVER_TELEGRAM", "true")

    with pytest.raises(ErreurConfiguration) as capture:
        charger_parametres()

    assert "TELEGRAM_BOT_TOKEN" in str(capture.value)
    assert "TELEGRAM_CHAT_ID" in str(capture.value)


def test_parametre_production_exige_cle_forte(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONNEMENT", "production")

    with pytest.raises(ErreurConfiguration, match="CLE_SECRETE"):
        charger_parametres()


def test_valeur_secrete_n_est_pas_affichee_dans_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "secret-court"
    monkeypatch.setenv("CLE_SECRETE", secret)

    with pytest.raises(ErreurConfiguration) as capture:
        charger_parametres()

    assert secret not in str(capture.value)


def test_port_smtp_est_borne(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMAIL_PORT", "70000")

    with pytest.raises(ErreurConfiguration, match="EMAIL_PORT"):
        charger_parametres()


def test_activation_email_valide_smtp_et_authentification_en_paire() -> None:
    parametres = Parametres(
        _env_file=None,
        ACTIVER_EMAIL=True,
        EMAIL_HOTE="smtp.example.test",
        EMAIL_EXPEDITEUR="brvm@example.test",
    )
    assert parametres.activer_email

    with pytest.raises(ValidationError, match="EMAIL_UTILISATEUR et EMAIL_MOT_DE_PASSE"):
        Parametres(
            _env_file=None,
            ACTIVER_EMAIL=True,
            EMAIL_HOTE="smtp.example.test",
            EMAIL_EXPEDITEUR="brvm@example.test",
            EMAIL_UTILISATEUR="user",
        )


def test_fuseau_horaire_invalide_est_signale(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FUSEAU_HORAIRE", "not/a-real-timezone")

    with pytest.raises(ErreurConfiguration, match="FUSEAU_HORAIRE"):
        charger_parametres()


def test_journalisation_valide_et_rejette_niveau_inconnu() -> None:
    logger = logging.getLogger()
    niveau_precedent = logger.level
    try:
        configurer_journalisation("warning")
        assert logger.level == logging.WARNING
        with pytest.raises(ErreurConfiguration, match="Niveau de journalisation"):
            configurer_journalisation("TRACE")
    finally:
        logger.setLevel(niveau_precedent)
