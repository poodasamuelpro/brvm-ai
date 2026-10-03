"""Validation et normalisation des lignes brutes de cours BRVM, sans correction silencieuse.

Chaque ligne produit soit une observation normalisée, soit un rejet motivé. Les
anomalies non bloquantes sont conservées comme avertissements traçables.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

from brvm_ia.collecte.sources.donnees_marche import LigneBruteCours, PageCoursActions
from brvm_ia.exceptions import ErreurValidationDonnees

_MOTIF_SYMBOLE = re.compile(r"^[A-Z]{3,6}$")
_TOLERANCE_VARIATION = Decimal("0.011")

Gravite = Literal["info", "warning", "error"]


@dataclass(frozen=True, slots=True)
class Constat:
    """Constat de qualité; `regle` est stable pour l’audit (data_quality_issue.rule_code)."""

    regle: str
    gravite: Gravite
    description: str


@dataclass(frozen=True, slots=True)
class CoursNormalise:
    """Observation journalière normalisée. Plus haut/plus bas : non publiés, donc absents."""

    symbole: str
    nom: str
    date_seance: date
    volume: Decimal
    ouverture: Decimal | None
    cloture: Decimal
    cours_veille_publie: Decimal
    variation_publiee_pct: Decimal


@dataclass(frozen=True, slots=True)
class ResultatLigne:
    ligne: LigneBruteCours
    cours: CoursNormalise | None
    constats: tuple[Constat, ...] = field(default_factory=tuple)

    @property
    def est_rejetee(self) -> bool:
        return self.cours is None


def convertir_nombre_fr(texte: str) -> Decimal:
    """Convertit « 35 239 » ou « -0,35 » en Decimal; refuse toute autre forme."""
    nettoye = texte.replace("\u202f", "").replace("\xa0", "").replace(" ", "").replace(",", ".")
    if not re.fullmatch(r"-?\d+(\.\d+)?", nettoye):
        raise ErreurValidationDonnees("Nombre au format inattendu.")
    try:
        return Decimal(nettoye)
    except InvalidOperation:
        raise ErreurValidationDonnees("Nombre non convertible.") from None


def date_seance_de_page(page: PageCoursActions, maintenant: datetime) -> date:
    """La date de séance est la date de « Dernière mise à jour » d’une séance fermée.

    Une page consultée pendant la séance (non fermée) n’est pas une donnée de fin
    de séance : elle est refusée plutôt que d’enregistrer des cours provisoires.
    """
    if not page.seance_fermee:
        raise ErreurValidationDonnees("Séance BRVM non fermée : cours non définitifs.")
    date_seance = page.mise_a_jour_source.date()
    if page.mise_a_jour_source > maintenant.astimezone(page.mise_a_jour_source.tzinfo):
        raise ErreurValidationDonnees("Date de mise à jour BRVM dans le futur.")
    if date_seance.isoweekday() > 5:
        raise ErreurValidationDonnees("Date de séance BRVM tombant un week-end.")
    return date_seance


def valider_ligne(ligne: LigneBruteCours, date_seance: date) -> ResultatLigne:
    """Valide une ligne publiée; aucune valeur n’est déduite ou remplacée."""
    donnees = ligne.en_dictionnaire()
    constats: list[Constat] = []

    def rejeter(regle: str, description: str) -> ResultatLigne:
        constats.append(Constat(regle, "error", description))
        return ResultatLigne(ligne, None, tuple(constats))

    symbole = donnees["Symbole"].strip()
    nom = donnees["Nom"].strip()
    if not _MOTIF_SYMBOLE.fullmatch(symbole):
        return rejeter("symbole_invalide", "Symbole absent ou hors format [A-Z]{3,6}.")
    if not nom:
        return rejeter("nom_absent", "Nom de la valeur absent.")

    valeurs: dict[str, Decimal] = {}
    for colonne in (
        "Volume",
        "Cours veille (FCFA)",
        "Cours Ouverture (FCFA)",
        "Cours Clôture (FCFA)",
        "Variation (%)",
    ):
        try:
            valeurs[colonne] = convertir_nombre_fr(donnees[colonne])
        except ErreurValidationDonnees:
            return rejeter("nombre_invalide", f"Valeur non numérique : colonne « {colonne} ».")

    volume = valeurs["Volume"]
    veille = valeurs["Cours veille (FCFA)"]
    ouverture = valeurs["Cours Ouverture (FCFA)"]
    cloture = valeurs["Cours Clôture (FCFA)"]
    variation = valeurs["Variation (%)"]

    if volume < 0 or volume != volume.to_integral_value():
        return rejeter("volume_invalide", "Volume négatif ou non entier.")
    if cloture <= 0:
        return rejeter("cloture_non_positive", "Cours de clôture nul ou négatif.")
    if ouverture < 0 or veille < 0:
        return rejeter("prix_negatif", "Cours d’ouverture ou de veille négatif.")

    ouverture_normalisee: Decimal | None = ouverture
    if volume == 0:
        constats.append(
            Constat(
                "aucune_transaction",
                "info",
                "Volume nul : la clôture publiée est un cours de référence sans échange; "
                "l’ouverture publiée (0) est stockée comme absente.",
            )
        )
        if ouverture != 0:
            constats.append(
                Constat("ouverture_sans_volume", "warning", "Ouverture non nulle avec volume nul.")
            )
        ouverture_normalisee = ouverture if ouverture > 0 else None
    elif ouverture == 0:
        return rejeter("ouverture_nulle_avec_volume", "Ouverture nulle malgré un volume positif.")

    if veille > 0:
        calculee = ((cloture / veille) - 1) * 100
        if abs(calculee - variation) > _TOLERANCE_VARIATION:
            constats.append(
                Constat(
                    "variation_incoherente_cours_veille",
                    "info",
                    "La variation publiée ne correspond pas à (clôture / cours veille publié - 1); "
                    "le cours veille publié n’est donc pas utilisé comme clôture précédente.",
                )
            )

    cours = CoursNormalise(
        symbole=symbole,
        nom=nom,
        date_seance=date_seance,
        volume=volume,
        ouverture=ouverture_normalisee,
        cloture=cloture,
        cours_veille_publie=veille,
        variation_publiee_pct=variation,
    )
    return ResultatLigne(ligne, cours, tuple(constats))


def valider_page(page: PageCoursActions, maintenant: datetime) -> tuple[date, list[ResultatLigne]]:
    """Valide toutes les lignes; un symbole en double rejette toutes ses occurrences."""
    date_seance = date_seance_de_page(page, maintenant)
    resultats = [valider_ligne(ligne, date_seance) for ligne in page.lignes]

    occurrences: dict[str, int] = {}
    for ligne in page.lignes:
        occurrences[ligne.cellules[0]] = occurrences.get(ligne.cellules[0], 0) + 1
    for index, resultat in enumerate(resultats):
        if occurrences[resultat.ligne.cellules[0]] > 1:
            resultats[index] = ResultatLigne(
                resultat.ligne,
                None,
                (
                    *resultat.constats,
                    Constat("symbole_duplique", "error", "Symbole présent plusieurs fois."),
                ),
            )
    return date_seance, resultats
