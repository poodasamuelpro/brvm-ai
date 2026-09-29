"""Configuration centralisée de la journalisation standard Python."""

from __future__ import annotations

import logging

from brvm_ia.exceptions import ErreurConfiguration

_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


def configurer_journalisation(niveau: str = "INFO") -> None:
    """Configure le logger racine après validation du niveau demandé."""
    niveau_normalise = niveau.strip().upper()
    niveaux = logging.getLevelNamesMapping()
    valeur_niveau = niveaux.get(niveau_normalise)
    if not isinstance(valeur_niveau, int) or niveau_normalise not in {
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    }:
        raise ErreurConfiguration(
            "Niveau de journalisation invalide; valeurs permises: DEBUG, INFO, "
            "WARNING, ERROR, CRITICAL."
        )

    racine = logging.getLogger()
    racine.setLevel(valeur_niveau)
    if not racine.handlers:
        gestionnaire = logging.StreamHandler()
        gestionnaire.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT))
        racine.addHandler(gestionnaire)
