"""Collecte réelle des cours de fin de séance BRVM et enregistrement dans le schéma `brvm`.

Usage :
    python scripts/lancer_pipeline.py            # télécharge brvm.org puis enregistre
    python scripts/lancer_pipeline.py --sec      # télécharge et valide sans écrire en base

Requiert ACTIVER_BASE_DE_DONNEES=true et BASE_DE_DONNEES_URL (environnement ou .env local).

Codes de sortie : 0 succès (y compris « séance déjà collectée »), 2 séance non fermée
(cours provisoires, rien n’est écrit : relancer plus tard), 1 échec. Chaque échec
survenant après l’accès à la base est tracé dans brvm.pipeline_run / pipeline_run_error.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from brvm_ia.collecte.sources.donnees_marche import (  # noqa: E402
    URL_COURS_ACTIONS,
    telecharger_page_cours_actions,
)
from brvm_ia.collecte.validateurs import valider_page  # noqa: E402
from brvm_ia.configuration import obtenir_parametres  # noqa: E402
from brvm_ia.exceptions import (  # noqa: E402
    ErreurBaseDeDonnees,
    ErreurBRVM,
    ErreurCollecte,
    ErreurValidationDonnees,
)
from brvm_ia.journalisation import configurer_journalisation  # noqa: E402

journal = logging.getLogger("brvm_ia.collecte.brvm")


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--sec", action="store_true", help="ne pas écrire en base")
    arguments = analyseur.parse_args()
    parametres = obtenir_parametres()
    configurer_journalisation(parametres.niveau_journalisation)

    try:
        page = telecharger_page_cours_actions()
        date_seance, resultats = valider_page(page, datetime.now(UTC))
    except ErreurValidationDonnees as erreur:
        if "non fermée" in str(erreur):
            journal.warning("Séance BRVM non fermée : aucune écriture, relancer plus tard.")
            return 2
        return _echec(arguments.sec, "validation_page", str(erreur))
    except ErreurCollecte as erreur:
        return _echec(arguments.sec, "collecte_page", str(erreur))

    rejets = sum(r.est_rejetee for r in resultats)
    journal.info(
        "BRVM %s : %d lignes reçues, %d rejetées (mise à jour source %s).",
        date_seance,
        len(resultats),
        rejets,
        page.mise_a_jour_source.isoformat(),
    )
    if arguments.sec:
        return 0

    from brvm_ia.base_de_donnees.moteur import GestionnaireBaseDeDonnees
    from brvm_ia.collecte.pipeline import PipelineCoursBRVM

    try:
        with GestionnaireBaseDeDonnees(parametres) as gestionnaire:
            gestionnaire.verifier_connexion()
            bilan = PipelineCoursBRVM(gestionnaire).enregistrer(page)
    except ErreurBRVM as erreur:
        return _echec(False, "enregistrement", str(erreur))
    journal.info("Bilan : %s", bilan)
    return 0


def _echec(sans_base: bool, code: str, resume: str) -> int:
    """Journalise l’échec; tente de le tracer en base (transaction séparée)."""
    journal.error("Échec (%s) : %s", code, resume)
    if sans_base:
        return 1
    try:
        from brvm_ia.base_de_donnees.moteur import GestionnaireBaseDeDonnees
        from brvm_ia.collecte.pipeline import PipelineCoursBRVM

        with GestionnaireBaseDeDonnees(obtenir_parametres()) as gestionnaire:
            PipelineCoursBRVM(gestionnaire).journaliser_interruption(
                "failed", code, resume[:500], {"url": URL_COURS_ACTIONS}
            )
    except (ErreurBRVM, ErreurBaseDeDonnees):
        journal.error("Impossible de tracer l’échec dans brvm.pipeline_run.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
