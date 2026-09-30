"""Socle minimal du bot Telegram EMMA (BRVM-AI).

Ce module ne construit que le tuyau Telegram → Python : la commande `/start`
répond à un utilisateur autorisé, et refuse proprement un utilisateur non
autorisé. Aucun signal, aucune collecte BRVM et aucun agent conversationnel
ne sont implémentés ici.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from brvm_ia.configuration.parametres import Parametres, obtenir_parametres
from brvm_ia.exceptions import ErreurConfiguration
from brvm_ia.telegram.autorisation import utilisateur_est_autorise

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

_LOGGER = logging.getLogger(__name__)

_MESSAGE_BIENVENUE = (
    "Bonjour 👋\n"
    "Je suis EMMA, l'assistant BRVM-AI.\n"
    "Je suis actuellement en cours de configuration."
)

_MESSAGE_REFUS = "Accès refusé.\nCe bot est privé pendant sa phase de développement."


async def _gerer_commande_start(update: Update, contexte: ContextTypes.DEFAULT_TYPE) -> None:
    """Répond à `/start`; refuse proprement un utilisateur non autorisé."""
    parametres: Parametres = contexte.bot_data["parametres"]
    utilisateur = update.effective_user
    message = update.effective_message
    if utilisateur is None or message is None:
        return

    if not utilisateur_est_autorise(utilisateur.id, parametres):
        _LOGGER.warning("Accès Telegram refusé pour un identifiant non autorisé.")
        await message.reply_text(_MESSAGE_REFUS)
        return

    _LOGGER.info("Commande /start traitée pour un utilisateur autorisé.")
    await message.reply_text(_MESSAGE_BIENVENUE)


def construire_application(parametres: Parametres | None = None) -> Any:
    """Construit l'application Telegram sans la démarrer.

    Le jeton est lu depuis les paramètres validés (SecretStr) et n'est jamais
    journalisé. La construction échoue explicitement si Telegram est
    désactivé, si le jeton est absent, ou si la dépendance optionnelle
    `python-telegram-bot` n'est pas installée.
    """
    configuration = parametres or obtenir_parametres()
    if not configuration.activer_telegram:
        raise ErreurConfiguration(
            "Telegram désactivé; définir ACTIVER_TELEGRAM=true pour l'activer."
        )
    if configuration.telegram_bot_token is None:
        raise ErreurConfiguration("TELEGRAM_BOT_TOKEN est requis lorsque Telegram est activé.")

    try:
        from telegram.ext import ApplicationBuilder, CommandHandler
    except ImportError:
        raise ErreurConfiguration(
            "L'intégration Telegram requiert l'extra optionnel `telegram` du paquet."
        ) from None

    application = (
        ApplicationBuilder().token(configuration.telegram_bot_token.get_secret_value()).build()
    )
    application.bot_data["parametres"] = configuration
    application.add_handler(CommandHandler("start", _gerer_commande_start))
    return application


def executer_bot(parametres: Parametres | None = None) -> None:
    """Démarre le bot en scrutation (polling); bloquant, destiné à un process dédié."""
    application = construire_application(parametres)
    _LOGGER.info("Démarrage du bot Telegram EMMA (polling).")
    application.run_polling(allowed_updates=["message"])
