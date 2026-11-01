"""Compare et journalise les divergences de cours pour un titre et une séance."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from brvm_ia.base_de_donnees.moteur import GestionnaireBaseDeDonnees  # noqa: E402
from brvm_ia.collecte.consolidation import (  # noqa: E402
    comparer_cours,
    journaliser_divergences,
)
from brvm_ia.configuration import obtenir_parametres  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--security-id", required=True, type=UUID)
    parser.add_argument("--date", required=True, type=date.fromisoformat)
    parser.add_argument("--tolerance-pct", type=str, default="0.01")
    args = parser.parse_args()
    from decimal import Decimal

    with GestionnaireBaseDeDonnees(obtenir_parametres()) as gestionnaire:
        with gestionnaire.session() as session:
            rapport = comparer_cours(
                session,
                security_id=args.security_id,
                market_date=args.date,
                tolerance_pct=Decimal(args.tolerance_pct),
            )
            anomalies = journaliser_divergences(session, rapport)
    print(json.dumps({
        "security_id": str(rapport.security_id),
        "market_date": rapport.market_date.isoformat(),
        "reference_source": rapport.reference_source,
        "status": rapport.status,
        "observations": len(rapport.observations),
        "divergences": list(rapport.divergences),
        "anomalies_creees": anomalies,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
