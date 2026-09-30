"""Contrats de lecture PostgreSQL vérifiés par mocks, sans serveur ou données marché."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

import pandas as pd
import pytest
from pydantic import SecretStr

from brvm_ia.base_de_donnees.depots import DepotDonneesPostgres
from brvm_ia.base_de_donnees.moteur import GestionnaireBaseDeDonnees
from brvm_ia.configuration.parametres import Parametres
from brvm_ia.exceptions import ErreurBaseDeDonnees, ErreurConfiguration, ErreurValidationDonnees


def _parametres_base(url: str | None = None) -> Parametres:
    return Parametres(
        _env_file=None,
        ACTIVER_BASE_DE_DONNEES=url is not None,
        BASE_DE_DONNEES_URL=SecretStr(url) if url is not None else None,
    )


def _url_postgresql_de_test() -> str:
    """Construit une URL avec un faux mot de passe sans stocker un URI littéral."""
    return "postgresql://" + "brvm_user:secret-test" + "@127.0.0.1:5432/brvm"


def test_base_desactivee_est_refusee_sans_tenter_de_connexion() -> None:
    with pytest.raises(ErreurConfiguration, match="ACTIVER_BASE_DE_DONNEES"):
        GestionnaireBaseDeDonnees(_parametres_base())


def test_url_postgresql_est_masquee_et_pool_prepare_sans_connexion() -> None:
    manager = GestionnaireBaseDeDonnees(_parametres_base(_url_postgresql_de_test()))
    try:
        assert manager.moteur.url.drivername == "postgresql+psycopg"
        assert "secret-test" not in str(manager.moteur.url)
        assert manager.moteur.echo is False
    finally:
        manager.fermer()


def test_manager_ferme_refuse_reutilisation() -> None:
    manager = GestionnaireBaseDeDonnees(
        _parametres_base(
            _url_postgresql_de_test().replace("postgresql://", "postgresql+psycopg://")
        )
    )
    manager.fermer()
    with pytest.raises(ErreurBaseDeDonnees, match="déjà fermé"):
        _ = manager.moteur


class _FausseConnexion:
    pass


class _FauxMoteur:
    @contextmanager
    def connect(self) -> Iterator[_FausseConnexion]:
        yield _FausseConnexion()


class _FauxGestionnaire:
    moteur = _FauxMoteur()


def test_depot_cours_utilise_parametres_et_exclut_donnees_non_validees(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture: dict[str, Any] = {}

    def lire(requete: object, connexion: object, params: dict[str, object]) -> pd.DataFrame:
        capture["requete"] = str(requete)
        capture["connexion"] = connexion
        capture["params"] = params
        return pd.DataFrame(columns=["market_date", "closing_price"])

    monkeypatch.setattr(pd, "read_sql_query", lire)
    security_id = uuid4()
    cutoff = datetime(2025, 3, 1, tzinfo=UTC)
    depot = DepotDonneesPostgres(_FauxGestionnaire())  # type: ignore[arg-type]

    resultat = depot.charger_cours(
        security_id,
        date(2025, 1, 1),
        date(2025, 2, 28),
        "1d",
        as_of=cutoff,
    )

    assert resultat.empty
    assert "validation_status = 'validated'" in capture["requete"]
    assert "collected_at <= :as_of" in capture["requete"]
    assert capture["params"]["security_id"] == security_id
    assert capture["params"]["as_of"] == cutoff


def test_depot_fundamental_exclut_faits_sans_disponibilite_lors_as_of(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture: dict[str, Any] = {}

    def lire(requete: object, connexion: object, params: dict[str, object]) -> pd.DataFrame:
        capture["requete"] = str(requete)
        capture["params"] = params
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", lire)
    company_id = uuid4()
    cutoff = datetime(2025, 3, 1, tzinfo=UTC)
    depot = DepotDonneesPostgres(_FauxGestionnaire())  # type: ignore[arg-type]

    depot.charger_faits_fondamentaux(
        company_id,
        date(2020, 1, 1),
        date(2024, 12, 31),
        as_of=cutoff,
    )

    assert "f.available_at IS NOT NULL" in capture["requete"]
    assert capture["params"]["company_id"] == company_id
    assert capture["params"]["as_of"] == cutoff


def test_depot_rejette_plage_inverse_et_date_as_of_naive() -> None:
    depot = DepotDonneesPostgres(_FauxGestionnaire())  # type: ignore[arg-type]
    with pytest.raises(ErreurValidationDonnees, match="date_fin"):
        depot.charger_cours(uuid4(), date(2025, 2, 2), date(2025, 2, 1), "1d")
    with pytest.raises(ErreurValidationDonnees, match="fuseau horaire"):
        depot.charger_cours(uuid4(), date(2025, 1, 1), date(2025, 2, 1), "1d", datetime(2025, 2, 1))
