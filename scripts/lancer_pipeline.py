"""Collecte réelle des cours de fin de séance BRVM et enregistrement dans le schéma `brvm`.

Usage :
    python scripts/lancer_pipeline.py            # télécharge brvm.org puis enregistre
    python scripts/lancer_pipeline.py --sec      # télécharge et valide sans écrire en base

Requiert ACTIVER_BASE_DE_DONNEES=true et BASE_DE_DONNEES_URL (environnement ou .env local).
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from brvm_ia.collecte.sources.donnees_marche import telecharger_page_cours_actions  # noqa: E402
from brvm_ia.collecte.validateurs import valider_page  # noqa: E402
from brvm_ia.configuration import obtenir_parametres  # noqa: E402
from brvm_ia.exceptions import ErreurBRVM  # noqa: E402


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--sec", action="store_true", help="ne pas écrire en base")
    arguments = analyseur.parse_args()

    try:
        page = telecharger_page_cours_actions()
        date_seance, resultats = valider_page(page, datetime.now(UTC))
        rejets = sum(r.est_rejetee for r in resultats)
        print(
            f"BRVM {date_seance} : {len(resultats)} lignes reçues, {rejets} rejetées "
            f"(mise à jour source {page.mise_a_jour_source.isoformat()})."
        )
        if arguments.sec:
            return 0

        from brvm_ia.base_de_donnees.moteur import GestionnaireBaseDeDonnees
        from brvm_ia.collecte.pipeline import PipelineCoursBRVM

        with GestionnaireBaseDeDonnees(obtenir_parametres()) as gestionnaire:
            gestionnaire.verifier_connexion()
            bilan = PipelineCoursBRVM(gestionnaire).enregistrer(page)
        print(bilan)
    except ErreurBRVM as erreur:
        print(f"Échec : {erreur}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
