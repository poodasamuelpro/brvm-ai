"""Tests du socle du bot Telegram; aucune connexion réseau réelle n'est faite.

`ApplicationBuilder().build()` de python-telegram-bot ne contacte pas
Telegram tant qu'aucun appel réseau (polling, webhook, envoi) n'est déclenché :
ces tests restent donc hors-ligne.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from brvm_ia.configuration.parametres import Parametres
from brvm_ia.exceptions import ErreurConfiguration
from brvm_ia.telegram.bot import _gerer_commande_start, construire_application


def _parametres_telegram(
    token: str | None = "jeton-de-test",
    actif: bool = True,
    admin: int | None = None,
    autorises: str | None = None,
) -> Parametres:
    valeurs: dict[str, object] = {
        "_env_file": None,
        "ACTIVER_TELEGRAM": actif,
    }
    if token is not None:
        valeurs["TELEGRAM_BOT_TOKEN"] = token
    if admin is not None:
        valeurs["TELEGRAM_ADMIN_USER_ID"] = admin
    if autorises is not None:
        valeurs["TELEGRAM_UTILISATEURS_AUTORISES"] = autorises
    return Parametres(**valeurs)


def test_construire_application_refuse_si_telegram_desactive() -> None:
    parametres = Parametres(_env_file=None, ACTIVER_TELEGRAM=False)

    with pytest.raises(ErreurConfiguration, match="ACTIVER_TELEGRAM"):
        construire_application(parametres)


def test_construire_application_refuse_sans_jeton() -> None:
    parametres = Parametres.model_construct(
        activer_telegram=True,
        telegram_bot_token=None,
        telegram_admin_user_id=None,
        telegram_utilisateurs_autorises=frozenset(),
    )

    with pytest.raises(ErreurConfiguration, match="TELEGRAM_BOT_TOKEN"):
        construire_application(parametres)


def test_construire_application_prepare_le_gestionnaire_start() -> None:
    parametres = _parametres_telegram()

    application = construire_application(parametres)

    assert application.bot_data["parametres"] is parametres
    assert len(application.handlers[0]) == 1


@pytest.mark.asyncio
async def test_gerer_commande_start_repond_a_un_utilisateur_autorise() -> None:
    parametres = _parametres_telegram(admin=42)
    contexte = MagicMock()
    contexte.bot_data = {"parametres": parametres}

    update = MagicMock()
    update.effective_user.id = 42
    update.effective_message.reply_text = AsyncMock()

    await _gerer_commande_start(update, contexte)

    update.effective_message.reply_text.assert_awaited_once()
    (texte_envoye,) = update.effective_message.reply_text.await_args.args
    assert "EMMA" in texte_envoye


@pytest.mark.asyncio
async def test_gerer_commande_start_refuse_un_utilisateur_non_autorise() -> None:
    parametres = _parametres_telegram(admin=42)
    contexte = MagicMock()
    contexte.bot_data = {"parametres": parametres}

    update = MagicMock()
    update.effective_user.id = 999
    update.effective_message.reply_text = AsyncMock()

    await _gerer_commande_start(update, contexte)

    update.effective_message.reply_text.assert_awaited_once()
    (texte_envoye,) = update.effective_message.reply_text.await_args.args
    assert "refusé" in texte_envoye.lower()
