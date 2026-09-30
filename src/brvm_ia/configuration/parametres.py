"""Paramètres fortement typés chargés depuis l’environnement et le fichier .env local."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AnyHttpUrl, Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from brvm_ia.exceptions import ErreurConfiguration

Environnement = Literal["developpement", "test", "production"]
NiveauJournalisation = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Parametres(BaseSettings):
    """Configuration d’exécution; les intégrations restent désactivées par défaut."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        case_sensitive=True,
        extra="ignore",
        hide_input_in_errors=True,
    )

    environnement: Environnement = Field("developpement", validation_alias="ENVIRONNEMENT")
    version_application: str = Field("0.1.0", validation_alias="VERSION_APPLICATION")
    niveau_journalisation: NiveauJournalisation = Field(
        "INFO", validation_alias="NIVEAU_JOURNALISATION"
    )

    activer_base_de_donnees: bool = Field(False, validation_alias="ACTIVER_BASE_DE_DONNEES")
    base_de_donnees_url: SecretStr | None = Field(None, validation_alias="BASE_DE_DONNEES_URL")

    activer_api_interne: bool = Field(False, validation_alias="ACTIVER_API_INTERNE")
    url_api: AnyHttpUrl | None = Field(None, validation_alias="URL_API")
    cle_api_interne: SecretStr | None = Field(None, validation_alias="CLE_API_INTERNE")

    activer_api_donnees_marche: bool = Field(False, validation_alias="ACTIVER_API_DONNEES_MARCHE")
    cle_api_donnees_marche: SecretStr | None = Field(
        None, validation_alias="CLE_API_DONNEES_MARCHE"
    )

    activer_email: bool = Field(False, validation_alias="ACTIVER_EMAIL")
    email_hote: str | None = Field(None, validation_alias="EMAIL_HOTE")
    email_port: int = Field(587, ge=1, le=65535, validation_alias="EMAIL_PORT")
    email_utilisateur: str | None = Field(None, validation_alias="EMAIL_UTILISATEUR")
    email_mot_de_passe: SecretStr | None = Field(None, validation_alias="EMAIL_MOT_DE_PASSE")
    email_expediteur: str | None = Field(None, validation_alias="EMAIL_EXPEDITEUR")

    activer_telegram: bool = Field(False, validation_alias="ACTIVER_TELEGRAM")
    telegram_bot_token: SecretStr | None = Field(None, validation_alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = Field(None, validation_alias="TELEGRAM_CHAT_ID")
    telegram_admin_user_id: int | None = Field(None, validation_alias="TELEGRAM_ADMIN_USER_ID")
    telegram_utilisateurs_autorises: Annotated[frozenset[int], NoDecode] = Field(
        default_factory=frozenset, validation_alias="TELEGRAM_UTILISATEURS_AUTORISES"
    )

    activer_ia: bool = Field(False, validation_alias="ACTIVER_IA")
    fournisseur_ia: str | None = Field(None, validation_alias="FOURNISSEUR_IA")
    cle_api_ia: SecretStr | None = Field(None, validation_alias="CLE_API_IA")
    modele_ia: str | None = Field(None, validation_alias="MODELE_IA")

    activer_api: bool = Field(False, validation_alias="ACTIVER_API")
    cle_secrete: SecretStr | None = Field(None, validation_alias="CLE_SECRETE")

    frequence_collecte_minutes: int = Field(
        1440, ge=1, le=10080, validation_alias="FREQUENCE_COLLECTE_MINUTES"
    )
    fuseau_horaire: str = Field("Africa/Abidjan", validation_alias="FUSEAU_HORAIRE")
    nombre_max_tentatives: int = Field(3, ge=0, le=10, validation_alias="NOMBRE_MAX_TENTATIVES")

    @field_validator(
        "base_de_donnees_url",
        "cle_api_interne",
        "cle_api_donnees_marche",
        "email_hote",
        "email_utilisateur",
        "email_mot_de_passe",
        "email_expediteur",
        "telegram_bot_token",
        "telegram_chat_id",
        "fournisseur_ia",
        "cle_api_ia",
        "modele_ia",
        "cle_secrete",
        mode="before",
    )
    @classmethod
    def convertir_chaine_vide_en_absence(cls, valeur: object) -> object:
        """Traite une variable vide comme non configurée, sans inventer de valeur."""
        if isinstance(valeur, str) and not valeur.strip():
            return None
        return valeur

    @field_validator("version_application", "email_hote", "email_utilisateur", "email_expediteur")
    @classmethod
    def nettoyer_chaine(cls, valeur: str | None) -> str | None:
        return valeur.strip() if valeur is not None else None

    @field_validator("telegram_utilisateurs_autorises", mode="before")
    @classmethod
    def analyser_utilisateurs_autorises(cls, valeur: object) -> object:
        """Accepte une liste d'identifiants Telegram séparés par des virgules."""
        if valeur is None or isinstance(valeur, frozenset | set | list | tuple):
            return valeur
        if isinstance(valeur, str):
            if not valeur.strip():
                return frozenset()
            try:
                return frozenset(
                    int(partie.strip()) for partie in valeur.split(",") if partie.strip()
                )
            except ValueError as erreur:
                raise ValueError(
                    "TELEGRAM_UTILISATEURS_AUTORISES doit contenir des identifiants "
                    "numériques séparés par des virgules."
                ) from erreur
        return valeur

    @field_validator("base_de_donnees_url")
    @classmethod
    def valider_url_base(cls, valeur: SecretStr | None) -> SecretStr | None:
        if valeur is None:
            return None
        try:
            parsed = urlsplit(valeur.get_secret_value())
        except ValueError as erreur:
            raise ValueError("BASE_DE_DONNEES_URL doit être une URL valide.") from erreur
        if parsed.scheme not in {"postgresql", "postgresql+psycopg"} or not parsed.hostname:
            raise ValueError(
                "BASE_DE_DONNEES_URL doit utiliser PostgreSQL et contenir un hôte valide."
            )
        return valeur

    @field_validator("email_expediteur")
    @classmethod
    def valider_expediteur(cls, valeur: str | None) -> str | None:
        if valeur is not None and (
            valeur.count("@") != 1 or valeur.startswith("@") or valeur.endswith("@")
        ):
            raise ValueError("EMAIL_EXPEDITEUR doit être une adresse email valide.")
        return valeur

    @field_validator("cle_secrete")
    @classmethod
    def valider_longueur_cle_secrete(cls, valeur: SecretStr | None) -> SecretStr | None:
        if valeur is not None and len(valeur.get_secret_value()) < 32:
            raise ValueError("CLE_SECRETE doit contenir au moins 32 caractères.")
        return valeur

    @field_validator("fuseau_horaire")
    @classmethod
    def valider_fuseau_horaire(cls, valeur: str) -> str:
        try:
            ZoneInfo(valeur)
        except ZoneInfoNotFoundError as erreur:
            raise ValueError("FUSEAU_HORAIRE doit être un identifiant IANA valide.") from erreur
        return valeur

    @model_validator(mode="after")
    def valider_integrations_activees(self) -> Parametres:
        exigences = (
            (self.activer_base_de_donnees, (("BASE_DE_DONNEES_URL", self.base_de_donnees_url),)),
            (
                self.activer_api_interne,
                (("URL_API", self.url_api), ("CLE_API_INTERNE", self.cle_api_interne)),
            ),
            (
                self.activer_api_donnees_marche,
                (("CLE_API_DONNEES_MARCHE", self.cle_api_donnees_marche),),
            ),
            (
                self.activer_telegram,
                (("TELEGRAM_BOT_TOKEN", self.telegram_bot_token),),
            ),
            (
                self.activer_ia,
                (
                    ("FOURNISSEUR_IA", self.fournisseur_ia),
                    ("CLE_API_IA", self.cle_api_ia),
                    ("MODELE_IA", self.modele_ia),
                ),
            ),
        )
        manquants = [
            nom
            for activee, champs in exigences
            if activee
            for nom, valeur in champs
            if valeur is None
        ]
        if self.activer_email:
            champs_email = (
                ("EMAIL_HOTE", self.email_hote),
                ("EMAIL_EXPEDITEUR", self.email_expediteur),
            )
            manquants.extend(nom for nom, valeur in champs_email if valeur is None)
            if (self.email_utilisateur is None) != (self.email_mot_de_passe is None):
                raise ValueError(
                    "EMAIL_UTILISATEUR et EMAIL_MOT_DE_PASSE doivent être définis ensemble."
                )
        if self.activer_api and self.cle_secrete is None:
            manquants.append("CLE_SECRETE (32 caractères minimum lorsque l’API est activée)")
        if manquants:
            raise ValueError(
                "Variables obligatoires pour les fonctionnalités activées: "
                + ", ".join(manquants)
                + "."
            )
        return self


def charger_parametres() -> Parametres:
    """Charge les paramètres et traduit les erreurs en diagnostic sans valeurs secrètes."""
    try:
        return Parametres()
    except ValidationError as erreur:
        diagnostics: list[str] = []
        for detail in erreur.errors(include_input=False, include_url=False):
            emplacement = ".".join(str(partie) for partie in detail["loc"]) or "configuration"
            diagnostics.append(f"{emplacement}: {detail['msg']}")
        raise ErreurConfiguration("Configuration invalide: " + "; ".join(diagnostics)) from erreur


@lru_cache(maxsize=1)
def obtenir_parametres() -> Parametres:
    """Renvoie une instance de paramètres mise en cache pour le processus courant."""
    return charger_parametres()
