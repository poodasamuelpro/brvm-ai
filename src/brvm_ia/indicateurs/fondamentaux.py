"""Ratios fondamentaux calculés uniquement à partir d’éléments explicitement fournis."""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real


@dataclass(frozen=True, slots=True)
class DonneesFondamentales:
    """Données financières d’une période; ``None`` signifie indisponible, non zéro."""

    chiffre_affaires: float | None = None
    resultat_net: float | None = None
    capitaux_propres: float | None = None
    actifs: float | None = None
    passifs: float | None = None
    dividende_par_action: float | None = None
    benefice_par_action: float | None = None
    cours_action: float | None = None

    def __post_init__(self) -> None:
        valeurs = {
            "chiffre_affaires": self.chiffre_affaires,
            "resultat_net": self.resultat_net,
            "capitaux_propres": self.capitaux_propres,
            "actifs": self.actifs,
            "passifs": self.passifs,
            "dividende_par_action": self.dividende_par_action,
            "benefice_par_action": self.benefice_par_action,
            "cours_action": self.cours_action,
        }
        for nom, valeur in valeurs.items():
            if valeur is not None and (
                isinstance(valeur, bool)
                or not isinstance(valeur, Real)
                or not math.isfinite(float(valeur))
            ):
                raise ValueError(f"{nom} doit être une valeur numérique finie.")
        for nom, valeur in (
            ("chiffre_affaires", self.chiffre_affaires),
            ("actifs", self.actifs),
            ("passifs", self.passifs),
            ("dividende_par_action", self.dividende_par_action),
        ):
            if valeur is not None and valeur < 0:
                raise ValueError(f"{nom} ne peut pas être négatif.")
        if self.cours_action is not None and self.cours_action <= 0:
            raise ValueError("cours_action doit être strictement positif.")


@dataclass(frozen=True, slots=True)
class RatiosFondamentaux:
    """Ratios définis; ``None`` marque un résultat non calculable avec les données reçues."""

    marge_nette: float | None
    rentabilite_capitaux_propres: float | None
    rentabilite_actifs: float | None
    ratio_passifs_actifs: float | None
    rendement_dividende: float | None
    ratio_cours_benefice: float | None


def _ratio(numerateur: float | None, denominateur: float | None) -> float | None:
    if numerateur is None or denominateur is None or denominateur == 0:
        return None
    resultat = numerateur / denominateur
    return resultat if math.isfinite(resultat) else None


def calculer_ratios_fondamentaux(donnees: DonneesFondamentales) -> RatiosFondamentaux:
    """Calcule marges, rentabilités, endettement, rendement et PER sans imputation.

    Le PER n’est défini ici que pour un bénéfice par action strictement positif;
    les champs indisponibles ou non interprétables renvoient ``None``.
    """
    benefice_par_action = donnees.benefice_par_action
    cours_benefice = (
        _ratio(donnees.cours_action, benefice_par_action)
        if benefice_par_action is not None and benefice_par_action > 0
        else None
    )
    return RatiosFondamentaux(
        marge_nette=_ratio(donnees.resultat_net, donnees.chiffre_affaires),
        rentabilite_capitaux_propres=_ratio(donnees.resultat_net, donnees.capitaux_propres),
        rentabilite_actifs=_ratio(donnees.resultat_net, donnees.actifs),
        ratio_passifs_actifs=_ratio(donnees.passifs, donnees.actifs),
        rendement_dividende=_ratio(donnees.dividende_par_action, donnees.cours_action),
        ratio_cours_benefice=cours_benefice,
    )


def calculer_croissance(
    valeur_courante: float | None,
    valeur_precedente: float | None,
) -> float | None:
    """Calcule une croissance relative si les deux périodes et une base positive existent."""
    if valeur_courante is None or valeur_precedente is None or valeur_precedente <= 0:
        return None
    if not math.isfinite(valeur_courante) or not math.isfinite(valeur_precedente):
        raise ValueError("Les valeurs de croissance doivent être finies.")
    resultat = (valeur_courante - valeur_precedente) / valeur_precedente
    if not math.isfinite(resultat):
        raise ValueError("La croissance calculée dépasse les limites numériques.")
    return resultat
