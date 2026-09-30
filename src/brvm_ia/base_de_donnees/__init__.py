"""Accès optionnel à la base; le driver n’est chargé qu’à l’activation de l’intégration."""

from brvm_ia.base_de_donnees.moteur import GestionnaireBaseDeDonnees

__all__ = ["GestionnaireBaseDeDonnees"]
