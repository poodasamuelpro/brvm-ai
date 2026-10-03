"""Collecte d'historiques SIKA Finance pour les titres BRVM.

Le point ``/api/general/GetHistos`` est un endpoint interne observé sur la page
publique SIKA, pas une API officiellement documentée. Le module refuse toute
réponse ambiguë et remonte explicitement les blocages HTTP; il ne fabrique
aucune ligne historique.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from brvm_ia.exceptions import ErreurCollecte, ErreurValidationDonnees

URL_API_HISTORIQUES = "https://www.sikafinance.com/api/general/GetHistos"
URL_PAGE_HISTORIQUES = "https://www.sikafinance.com/marches/historiques/{ticker}"
CODE_SOURCE_SIKA = "SIKA_FINANCE"
XPERIOD_JOURNALIER = "D"
MAX_JOURS_REQUETE = 92
AGENT_UTILISATEUR = "BRVM-AI-collecteur/0.1 (+https://github.com/poodasamuelpro/brvm-ai)"


@dataclass(frozen=True, slots=True)
class BarreHistoriqueSIKA:
    """Une observation journalière conservant le ticker propre à SIKA."""

    ticker_sika: str
    date_seance: date
    ouverture: Decimal
    plus_haut: Decimal
    plus_bas: Decimal
    cloture: Decimal
    volume_titres: Decimal
    volume_fcfa: Decimal | None
    variation_pct: Decimal | None


def _valeur(objet: dict[str, Any], *noms: str) -> Any:
    for nom in noms:
        if nom in objet and objet[nom] not in (None, ""):
            return objet[nom]
    raise ErreurValidationDonnees(f"Champ historique SIKA absent: {noms[0]}.")


def _decimal(valeur: Any, champ: str, *, entier: bool = False) -> Decimal:
    texte = str(valeur).strip().replace("\u202f", "").replace("\xa0", "")
    texte = texte.replace(" ", "").replace(",", ".").replace("%", "")
    try:
        resultat = Decimal(texte)
    except (InvalidOperation, ValueError) as erreur:
        raise ErreurValidationDonnees(f"Valeur SIKA invalide pour {champ}.") from erreur
    if (
        not resultat.is_finite()
        or resultat < 0
        or (entier and resultat != resultat.to_integral_value())
    ):
        raise ErreurValidationDonnees(f"Valeur SIKA impossible pour {champ}.")
    return resultat


def _date(valeur: Any) -> date:
    texte = str(valeur).strip()
    for format_ in ("%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(texte, format_).date()
        except ValueError:
            pass
    raise ErreurValidationDonnees("Date historique SIKA non reconnue.")


def _lignes_reponse(reponse: Any) -> list[dict[str, Any]]:
    if isinstance(reponse, list):
        lignes = reponse
    elif isinstance(reponse, dict):
        lignes = reponse.get("data", reponse.get("datas", reponse.get("rows")))
    else:
        lignes = None
    if not isinstance(lignes, list) or not all(isinstance(ligne, dict) for ligne in lignes):
        raise ErreurValidationDonnees("Réponse historique SIKA sans liste de lignes exploitable.")
    return lignes


def analyser_reponse(reponse: Any, ticker_sika: str) -> tuple[BarreHistoriqueSIKA, ...]:
    """Normalise une réponse JSON SIKA sans correction silencieuse."""
    lignes: list[BarreHistoriqueSIKA] = []
    vues: set[date] = set()
    for ligne in _lignes_reponse(reponse):
        jour = _date(_valeur(ligne, "date", "Date", "dt"))
        if jour in vues:
            raise ErreurValidationDonnees(f"Doublon SIKA pour {ticker_sika} le {jour}.")
        vues.add(jour)
        ouverture = _decimal(_valeur(ligne, "open", "Open", "ouverture"), "ouverture")
        plus_haut = _decimal(_valeur(ligne, "high", "High", "plus_haut", "haut"), "plus haut")
        plus_bas = _decimal(_valeur(ligne, "low", "Low", "plus_bas", "bas"), "plus bas")
        cloture = _decimal(_valeur(ligne, "close", "Close", "cloture", "closing"), "clôture")
        volume = _decimal(
            _valeur(ligne, "volume", "Volume", "volume_titres"), "volume", entier=True
        )
        if not (plus_bas <= ouverture <= plus_haut and plus_bas <= cloture <= plus_haut):
            raise ErreurValidationDonnees(f"OHLC incohérent dans la ligne SIKA du {jour}.")
        volume_fcfa = None
        for nom in ("volume_fcfa", "VolumeFCFA", "value", "traded_value"):
            if nom in ligne and ligne[nom] not in (None, ""):
                volume_fcfa = _decimal(ligne[nom], "volume FCFA")
                break
        variation = None
        for nom in ("variation", "Variation", "variation_pct"):
            if nom in ligne and ligne[nom] not in (None, ""):
                variation = _decimal(ligne[nom], "variation")
                break
        lignes.append(
            BarreHistoriqueSIKA(
                ticker_sika,
                jour,
                ouverture,
                plus_haut,
                plus_bas,
                cloture,
                volume,
                volume_fcfa,
                variation,
            )
        )
    return tuple(sorted(lignes, key=lambda ligne: ligne.date_seance))


def recuperer_historique(
    ticker_sika: str,
    date_debut: date,
    date_fin: date,
    *,
    timeout_secondes: float = 30.0,
    url_api: str = URL_API_HISTORIQUES,
) -> tuple[BarreHistoriqueSIKA, ...]:
    """Récupère réellement l'historique journalier via le POST SIKA observé."""
    if not ticker_sika.strip():
        raise ValueError("ticker_sika ne peut pas être vide.")
    if date_fin < date_debut or date_fin - date_debut > timedelta(days=MAX_JOURS_REQUETE):
        raise ValueError("La plage SIKA doit être positive et ne pas dépasser 92 jours.")
    charge = {
        "ticker": ticker_sika,
        "datedeb": date_debut.isoformat(),
        "datefin": date_fin.isoformat(),
        "xperiod": XPERIOD_JOURNALIER,
    }
    requete = urllib.request.Request(
        url_api,
        data=json.dumps(charge).encode("utf-8"),
        headers={
            "User-Agent": AGENT_UTILISATEUR,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(requete, timeout=timeout_secondes) as reponse:
            if reponse.status != 200:
                raise ErreurCollecte(f"SIKA Finance a répondu HTTP {reponse.status}.")
            contenu = reponse.read()
    except urllib.error.HTTPError as erreur:
        if erreur.code == 404:
            raise ErreurCollecte(
                f"Ticker SIKA inconnu ou sans historique: {ticker_sika}."
            ) from None
        if erreur.code in {401, 403}:
            raise ErreurCollecte(
                "SIKA Finance bloque actuellement la collecte automatisée (HTTP 403/401)."
            ) from None
        raise ErreurCollecte(f"SIKA Finance a répondu HTTP {erreur.code}.") from None
    except (urllib.error.URLError, TimeoutError, OSError) as erreur:
        raise ErreurCollecte(f"Accès SIKA Finance impossible ({type(erreur).__name__}).") from None
    try:
        reponse_json = json.loads(contenu.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as erreur:
        raise ErreurCollecte("Réponse SIKA non JSON; aucune donnée enregistrée.") from erreur
    if isinstance(reponse_json, dict) and str(reponse_json.get("status", "")).lower() == "nodata":
        return ()
    return analyser_reponse(reponse_json, ticker_sika)
