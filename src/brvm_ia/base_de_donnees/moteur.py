"""Connexion PostgreSQL optionnelle, paresseuse et sans exposition de credentials."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from pydantic import SecretStr

from brvm_ia.configuration.parametres import Parametres, obtenir_parametres
from brvm_ia.exceptions import ErreurBaseDeDonnees, ErreurConfiguration

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import Session, sessionmaker


def _creer_moteur(url_secrete: SecretStr) -> Engine:
    """Crée un Engine non connecté, en forçant le driver psycopg 3 du projet."""
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.engine import make_url
    except ImportError:
        raise ErreurConfiguration(
            "L’accès PostgreSQL requiert l’extra optionnel `database` du paquet."
        ) from None

    try:
        url = make_url(url_secrete.get_secret_value())
        if url.get_backend_name() != "postgresql":
            raise ValueError("backend")
        if url.drivername == "postgresql":
            url = url.set(drivername="postgresql+psycopg")
        elif url.drivername != "postgresql+psycopg":
            raise ValueError("driver")
        return create_engine(
            url,
            echo=False,
            hide_parameters=True,
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=3,
            pool_timeout=10,
            pool_recycle=1800,
            connect_args={"connect_timeout": 5},
        )
    except Exception as erreur:
        # Les exceptions de parsing/driver peuvent contenir l’URL d’entrée.
        raise ErreurConfiguration(
            "Impossible de préparer la connexion PostgreSQL "
            f"({type(erreur).__name__}); la valeur de l’URL a été masquée."
        ) from None


class GestionnaireBaseDeDonnees:
    """Gère un moteur PostgreSQL et des sessions transactionnelles explicites.

    La construction ne contacte pas le serveur. Les paramètres de connexion sont lus
    seulement lorsque l’intégration est activée et son URL conservée en SecretStr.
    """

    def __init__(self, parametres: Parametres | None = None) -> None:
        configuration = parametres or obtenir_parametres()
        if not configuration.activer_base_de_donnees:
            raise ErreurConfiguration(
                "Base désactivée; définir ACTIVER_BASE_DE_DONNEES=true pour l’activer."
            )
        if configuration.base_de_donnees_url is None:
            raise ErreurConfiguration(
                "BASE_DE_DONNEES_URL est requise lorsque la base est activée."
            )

        self._moteur = _creer_moteur(configuration.base_de_donnees_url)
        try:
            from sqlalchemy.orm import sessionmaker
        except ImportError:
            self._moteur.dispose()
            raise ErreurConfiguration(
                "L’accès PostgreSQL requiert l’extra optionnel `database` du paquet."
            ) from None
        self._sessions: sessionmaker[Session] = sessionmaker(
            bind=self._moteur,
            autoflush=False,
            expire_on_commit=False,
        )
        self._ferme = False

    @property
    def moteur(self) -> Engine:
        """Moteur SQLAlchemy; aucun mot de passe n’est inclus dans sa représentation."""
        self._verifier_ouvert()
        return self._moteur

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Ouvre une unité de travail : commit si elle réussit, rollback sinon."""
        self._verifier_ouvert()
        try:
            from sqlalchemy.exc import SQLAlchemyError
        except ImportError:
            raise ErreurConfiguration(
                "L’accès PostgreSQL requiert l’extra optionnel `database` du paquet."
            ) from None
        try:
            with self._sessions.begin() as session:
                yield session
        except SQLAlchemyError:
            raise ErreurBaseDeDonnees(
                "La transaction PostgreSQL a échoué; les détails sensibles sont masqués."
            ) from None

    def verifier_connexion(self) -> None:
        """Vérifie l’accès par SELECT 1 sans journaliser l’URL ou les paramètres."""
        self._verifier_ouvert()
        try:
            from sqlalchemy import text
            from sqlalchemy.exc import SQLAlchemyError
        except ImportError:
            raise ErreurConfiguration(
                "L’accès PostgreSQL requiert l’extra optionnel `database` du paquet."
            ) from None
        try:
            with self._moteur.connect() as connexion:
                resultat: int = connexion.execute(text("SELECT 1")).scalar_one()
            if resultat != 1:
                raise ErreurBaseDeDonnees(
                    "Le contrôle PostgreSQL n’a pas renvoyé le résultat attendu."
                )
        except SQLAlchemyError:
            raise ErreurBaseDeDonnees(
                "La vérification de connexion PostgreSQL a échoué; l’URL est masquée."
            ) from None

    def fermer(self) -> None:
        """Libère le pool et rend ce gestionnaire inutilisable."""
        if not self._ferme:
            self._moteur.dispose()
            self._ferme = True

    def _verifier_ouvert(self) -> None:
        if self._ferme:
            raise ErreurBaseDeDonnees("Le gestionnaire PostgreSQL est déjà fermé.")

    def __enter__(self) -> GestionnaireBaseDeDonnees:
        self._verifier_ouvert()
        return self

    def __exit__(self, *_: object) -> None:
        self.fermer()
