"""Point d'entrée pour démarrer le bot Telegram EMMA en local ou en CI.

Usage :
    python scripts/lancer_bot_telegram.py

Le jeton est lu depuis l'environnement (`.env` local ou secrets GitHub) via
`brvm_ia.configuration.obtenir_parametres`; il n'est jamais écrit en dur ici.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from brvm_ia.configuration import obtenir_parametres  # noqa: E402
from brvm_ia.journalisation import configurer_journalisation  # noqa: E402
from brvm_ia.telegram import executer_bot  # noqa: E402


def main() -> None:
    parametres = obtenir_parametres()
    configurer_journalisation(parametres.niveau_journalisation)
    executer_bot(parametres)


if __name__ == "__main__":
    main()
