"""Intégration Telegram du bot EMMA; socle minimal et désactivé par défaut."""

from brvm_ia.telegram.autorisation import utilisateur_est_autorise
from brvm_ia.telegram.bot import construire_application, executer_bot

__all__ = ["construire_application", "executer_bot", "utilisateur_est_autorise"]
