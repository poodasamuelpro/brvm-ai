"""Contrôles de qualité OHLCV; la fonction rapporte les problèmes sans altérer les données."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

import numpy as np
import pandas as pd
from pandas import Series

from brvm_ia.exceptions import ErreurValidationDonnees

ColonnesMarche = (
    "date",
    "entreprise",
    "ticker",
    "ouverture",
    "plus_haut",
    "plus_bas",
    "cloture",
    "volume",
)
ColonnesPrix = ("ouverture", "plus_haut", "plus_bas", "cloture")


@dataclass(frozen=True, slots=True)
class AnomalieDonnee:
    """Anomalie localisée par position de ligne et colonne, sans recopier la donnée sensible."""

    code: str
    message: str
    gravite: Literal["erreur", "avertissement"]
    position_ligne: int | None = None
    colonne: str | None = None


@dataclass(frozen=True, slots=True)
class RapportValidation:
    """Résultat immuable des contrôles de qualité d’un lot de cotations."""

    nombre_lignes: int
    anomalies: tuple[AnomalieDonnee, ...]

    @property
    def est_valide(self) -> bool:
        """Vrai s’il n’y a pas d’anomalie bloquante; les avertissements restent visibles."""
        return not any(anomalie.gravite == "erreur" for anomalie in self.anomalies)

    @property
    def erreurs(self) -> tuple[AnomalieDonnee, ...]:
        """Retourne uniquement les anomalies qui invalident le lot."""
        return tuple(a for a in self.anomalies if a.gravite == "erreur")

    @property
    def avertissements(self) -> tuple[AnomalieDonnee, ...]:
        """Retourne les alertes non bloquantes qui exigent un examen humain."""
        return tuple(a for a in self.anomalies if a.gravite == "avertissement")


def _positions(masque: Series[Any]) -> list[int]:
    """Convertit un masque pandas en positions stables, même avec un index non unique."""
    return [i for i, actif in enumerate(masque.fillna(False).to_numpy(dtype=bool)) if actif]


def _anomalies_masque(
    anomalies: list[AnomalieDonnee],
    masque: Series[Any],
    *,
    code: str,
    message: str,
    colonne: str | None = None,
    gravite: Literal["erreur", "avertissement"] = "erreur",
) -> None:
    for position in _positions(masque):
        anomalies.append(AnomalieDonnee(code, message, gravite, position, colonne))


def valider_donnees_marche(
    donnees: pd.DataFrame,
    *,
    date_reference: datetime | None = None,
    dates_attendues: Iterable[datetime] | None = None,
    seuil_alerte_variation_absolue: float | None = None,
) -> RapportValidation:
    """Contrôle un DataFrame OHLCV attendu sans corriger silencieusement ses valeurs.

    ``seuil_alerte_variation_absolue`` est optionnel car une variation inhabituelle
    dépend de la source et du marché; quand il est fourni, il ne produit qu’un
    avertissement et ne rejette pas automatiquement une cotation réelle.
    """
    if seuil_alerte_variation_absolue is not None and (
        not math.isfinite(seuil_alerte_variation_absolue) or seuil_alerte_variation_absolue <= 0
    ):
        raise ValueError("Le seuil de variation doit être un nombre fini strictement positif.")

    anomalies: list[AnomalieDonnee] = []
    nombre_lignes = len(donnees)
    absentes = [colonne for colonne in ColonnesMarche if colonne not in donnees.columns]
    if absentes:
        anomalies.extend(
            AnomalieDonnee(
                "colonne_absente",
                f"Colonne obligatoire absente: {colonne}.",
                "erreur",
                colonne=colonne,
            )
            for colonne in absentes
        )
        return RapportValidation(nombre_lignes, tuple(anomalies))
    if nombre_lignes == 0:
        return RapportValidation(
            0,
            (
                AnomalieDonnee(
                    "lot_vide", "Le lot de cotations ne contient aucune ligne.", "erreur"
                ),
            ),
        )

    for colonne in ColonnesMarche:
        _anomalies_masque(
            anomalies,
            donnees[colonne].isna(),
            code="valeur_absente",
            message=f"Valeur absente dans {colonne}.",
            colonne=colonne,
        )

    ticker = donnees["ticker"].astype("string").str.strip()
    ticker_invalide = ticker.isna() | ticker.eq("")
    _anomalies_masque(
        anomalies,
        ticker_invalide,
        code="ticker_invalide",
        message="Le ticker doit être renseigné.",
        colonne="ticker",
    )

    dates = pd.to_datetime(donnees["date"], format="mixed", errors="coerce", utc=True)
    _anomalies_masque(
        anomalies,
        dates.isna(),
        code="date_invalide",
        message="La date doit être interprétable comme une date UTC.",
        colonne="date",
    )
    reference = pd.Timestamp(date_reference or datetime.now(UTC))
    if reference.tzinfo is None:
        reference = reference.tz_localize("UTC")
    else:
        reference = reference.tz_convert("UTC")
    _anomalies_masque(
        anomalies,
        dates.notna() & dates.gt(reference),
        code="date_future",
        message="Une cotation datée dans le futur ne peut pas être intégrée.",
        colonne="date",
    )
    if dates_attendues is not None:
        dates_calendrier = pd.DatetimeIndex(
            pd.to_datetime(list(dates_attendues), format="mixed", errors="coerce", utc=True)
        )
        if (
            len(dates_calendrier) == 0
            or dates_calendrier.hasnans
            or dates_calendrier.has_duplicates
        ):
            raise ValueError("Le calendrier fourni doit contenir des dates valides et uniques.")
        hors_calendrier = dates.notna() & ~dates.isin(dates_calendrier)
        _anomalies_masque(
            anomalies,
            hors_calendrier,
            code="date_hors_frequence",
            message="La date de cotation ne figure pas dans le calendrier attendu fourni.",
            colonne="date",
        )
        dates_valides = dates.dropna()
        if not dates_valides.empty:
            debut, fin = dates_valides.min(), dates_valides.max()
            calendrier_observe = dates_calendrier[
                (dates_calendrier >= debut) & (dates_calendrier <= fin)
            ]
            ticker_propre = donnees["ticker"].astype("string").str.strip()
            for symbole in ticker_propre.dropna().loc[lambda serie: serie.ne("")].unique():
                observees = dates.loc[ticker_propre.eq(symbole)].dropna()
                absentes_attendues = calendrier_observe.difference(pd.DatetimeIndex(observees))
                anomalies.extend(
                    AnomalieDonnee(
                        "cotation_attendue_absente",
                        f"Aucune cotation observée pour {symbole} le {date.isoformat()}; "
                        "vérifier le calendrier et la source.",
                        "avertissement",
                        colonne="date",
                    )
                    for date in absentes_attendues
                )

    numeriques: dict[str, Series[Any]] = {}
    for colonne in (*ColonnesPrix, "volume"):
        original = donnees[colonne]
        numerique = pd.to_numeric(original, errors="coerce").astype("float64")
        numeriques[colonne] = numerique
        _anomalies_masque(
            anomalies,
            original.notna() & numerique.isna(),
            code="valeur_non_numerique",
            message=f"La valeur de {colonne} doit être numérique.",
            colonne=colonne,
        )
        _anomalies_masque(
            anomalies,
            numerique.notna() & ~np.isfinite(numerique),
            code="valeur_non_finie",
            message=f"La valeur de {colonne} doit être finie.",
            colonne=colonne,
        )

    prix_valides = pd.Series(True, index=donnees.index)
    for colonne in ColonnesPrix:
        prix = numeriques[colonne]
        _anomalies_masque(
            anomalies,
            prix.notna() & prix.le(0),
            code="prix_non_positif",
            message="Les cours doivent être strictement positifs.",
            colonne=colonne,
        )
        prix_valides &= prix.notna() & np.isfinite(prix) & prix.gt(0)

    volume = numeriques["volume"]
    _anomalies_masque(
        anomalies,
        volume.notna() & volume.lt(0),
        code="volume_negatif",
        message="Le volume ne peut pas être négatif.",
        colonne="volume",
    )

    ouverture = numeriques["ouverture"]
    plus_haut = numeriques["plus_haut"]
    plus_bas = numeriques["plus_bas"]
    cloture = numeriques["cloture"]
    incoherent = prix_valides & (
        plus_haut.lt(ouverture)
        | plus_haut.lt(cloture)
        | plus_bas.gt(ouverture)
        | plus_bas.gt(cloture)
        | plus_bas.gt(plus_haut)
    )
    _anomalies_masque(
        anomalies,
        incoherent,
        code="ordre_ohlc_incoherent",
        message="Les bornes OHLC ne contiennent pas l’ouverture et la clôture.",
    )

    ticker_valide = ticker.notna() & ticker.ne("")
    positions_valides = dates.notna().reset_index(drop=True) & ticker_valide.reset_index(drop=True)
    cles = pd.DataFrame(
        {"ticker": ticker.reset_index(drop=True), "date": dates.reset_index(drop=True)}
    )
    doublons = cles.duplicated(subset=["ticker", "date"], keep=False) & positions_valides
    _anomalies_masque(
        anomalies,
        doublons,
        code="doublon_temporel",
        message="Une cotation existe déjà pour ce ticker et cet instant.",
        colonne="date",
    )

    if seuil_alerte_variation_absolue is not None:
        historique = pd.DataFrame(
            {
                "ticker": ticker.reset_index(drop=True),
                "date": dates.reset_index(drop=True),
                "cloture": cloture.reset_index(drop=True),
                "position": range(nombre_lignes),
            }
        )
        historique = historique.loc[positions_valides & prix_valides.reset_index(drop=True)]
        historique = historique.sort_values(["ticker", "date"], kind="stable")
        cours_precedent = historique.groupby("ticker", sort=False)["cloture"].shift(1)
        variations = historique["cloture"].div(cours_precedent).sub(1.0)
        alertes = variations.abs().gt(seuil_alerte_variation_absolue)
        for position in historique.loc[alertes.fillna(False), "position"].astype(int):
            anomalies.append(
                AnomalieDonnee(
                    "variation_extreme",
                    "La variation dépasse le seuil d’alerte configuré; vérifier la source.",
                    "avertissement",
                    int(position),
                    "cloture",
                )
            )

    return RapportValidation(nombre_lignes, tuple(anomalies))


def exiger_donnees_marche_valides(rapport: RapportValidation) -> None:
    """Lève une erreur explicite si le rapport contient des anomalies bloquantes."""
    if not rapport.est_valide:
        resume = ", ".join(
            f"{anomalie.code} (ligne {anomalie.position_ligne})"
            for anomalie in rapport.erreurs[:10]
        )
        raise ErreurValidationDonnees(
            f"Lot OHLCV invalide: {len(rapport.erreurs)} erreur(s); {resume}."
        )
