"""Règle d'autorisation des utilisateurs Telegram, testable sans réseau.

Le bot est privé pendant le développement. Un utilisateur est autorisé s'il
correspond à l'administrateur configuré (`TELEGRAM_ADMIN_USER_ID`) ou s'il
figure dans la liste blanche explicite (`TELEGRAM_UTILISATEURS_AUTORISES`).

Si aucune des deux variables n'est configurée, aucun utilisateur n'est
autorisé par défaut : l'absence de configuration ne doit jamais ouvrir le
bot à un fonctionnement public.
"""

from __future__ import annotations

from brvm_ia.configuration.parametres import Parametres


def utilisateur_est_autorise(identifiant_utilisateur: int, parametres: Parametres) -> bool:
    """Indique si `identifiant_utilisateur` peut utiliser le bot Telegram."""
    if parametres.telegram_admin_user_id == identifiant_utilisateur:
        return True
    return identifiant_utilisateur in parametres.telegram_utilisateurs_autorises
