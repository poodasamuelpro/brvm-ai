"""Tests de la règle d'autorisation Telegram; aucune connexion réseau."""

from __future__ import annotations

from brvm_ia.configuration.parametres import Parametres
from brvm_ia.telegram.autorisation import utilisateur_est_autorise


def _parametres_telegram(admin: int | None = None, autorises: str | None = None) -> Parametres:
    valeurs: dict[str, object] = {
        "_env_file": None,
        "ACTIVER_TELEGRAM": True,
        "TELEGRAM_BOT_TOKEN": "jeton-de-test",
    }
    if admin is not None:
        valeurs["TELEGRAM_ADMIN_USER_ID"] = admin
    if autorises is not None:
        valeurs["TELEGRAM_UTILISATEURS_AUTORISES"] = autorises
    return Parametres(**valeurs)


def test_aucune_configuration_ne_refuse_tout_le_monde() -> None:
    parametres = _parametres_telegram()

    assert not utilisateur_est_autorise(123, parametres)


def test_administrateur_est_toujours_autorise() -> None:
    parametres = _parametres_telegram(admin=42)

    assert utilisateur_est_autorise(42, parametres)
    assert not utilisateur_est_autorise(43, parametres)


def test_liste_blanche_autorise_les_identifiants_listes() -> None:
    parametres = _parametres_telegram(autorises="10,20,30")

    assert utilisateur_est_autorise(20, parametres)
    assert not utilisateur_est_autorise(99, parametres)


def test_administrateur_et_liste_blanche_se_cumulent() -> None:
    parametres = _parametres_telegram(admin=1, autorises="2,3")

    assert utilisateur_est_autorise(1, parametres)
    assert utilisateur_est_autorise(2, parametres)
    assert not utilisateur_est_autorise(4, parametres)
