"""Exceptions métier partagées par les modules BRVM-AI."""


class ErreurBRVM(Exception):
    """Classe de base des erreurs attendues de l’application."""


class ErreurConfiguration(ErreurBRVM):
    """Configuration absente, invalide ou incohérente."""


class ErreurBaseDeDonnees(ErreurBRVM):
    """Erreur d’accès ou d’intégrité liée à une base de données."""


class ErreurCollecte(ErreurBRVM):
    """Échec explicite d’une collecte de données externes."""


class ErreurValidationDonnees(ErreurBRVM):
    """Données reçues non conformes au contrat attendu."""


class ErreurAnalyse(ErreurBRVM):
    """Analyse impossible ou résultats non interprétables."""


class ErreurModele(ErreurBRVM):
    """Échec explicite lié à l’entraînement ou à l’évaluation d’un modèle."""


class ErreurNotification(ErreurBRVM):
    """Échec explicite lors de l’envoi d’une notification."""


class ErreurAgent(ErreurBRVM):
    """Échec explicite lié à un agent conversationnel."""
