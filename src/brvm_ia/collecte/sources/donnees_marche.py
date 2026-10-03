"""Source officielle BRVM : page publique « Cours des actions » (fin de séance).

Source vérifiée le 3 octobre 2026 : ``https://www.brvm.org/fr/cours-actions/0``
(HTTP 200, HTML public, sans authentification). La page expose un tableau par action
avec les colonnes ``Symbole``, ``Nom``, ``Volume``, ``Cours veille (FCFA)``,
``Cours Ouverture (FCFA)``, ``Cours Clôture (FCFA)``, ``Variation (%)`` ainsi que la
mention « Dernière mise à jour : <jour>, <j> <mois>, <aaaa> - <hh:mm> ».

Ce n’est pas une API documentée : la structure HTML peut changer. Le module échoue
explicitement si l’en-tête attendu n’est pas retrouvé. Aucune valeur n’est inventée :
le plus haut et le plus bas ne sont pas publiés par cette page et restent absents.
"""

from __future__ import annotations

import hashlib
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

from brvm_ia.exceptions import ErreurCollecte

URL_COURS_ACTIONS = "https://www.brvm.org/fr/cours-actions/0"
CODE_SOURCE_BRVM = "BRVM_SITE_OFFICIEL"
FUSEAU_BRVM = ZoneInfo("Africa/Abidjan")
EN_TETE_ATTENDU: tuple[str, ...] = (
    "Symbole",
    "Nom",
    "Volume",
    "Cours veille (FCFA)",
    "Cours Ouverture (FCFA)",
    "Cours Clôture (FCFA)",
    "Variation (%)",
)
AGENT_UTILISATEUR = "BRVM-AI-collecteur/0.1 (+https://github.com/poodasamuelpro/brvm-ai)"

_MOIS = {
    "janvier": 1,
    "février": 2,
    "fevrier": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "août": 8,
    "aout": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "décembre": 12,
    "decembre": 12,
}
_MOTIF_MISE_A_JOUR = re.compile(
    r"Derni[èe]re mise à jour\s*:\s*[^,]+,\s*(\d{1,2})\s+([^\s,]+),"
    r"\s*(\d{4})\s*-\s*(\d{1,2}):(\d{2})",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class LigneBruteCours:
    """Cellules d’une ligne telles que publiées (texte), avant toute conversion."""

    cellules: tuple[str, ...]

    def en_dictionnaire(self) -> dict[str, str]:
        return dict(zip(EN_TETE_ATTENDU, self.cellules, strict=True))


@dataclass(frozen=True, slots=True)
class PageCoursActions:
    """Instantané brut de la page, avec les éléments de traçabilité nécessaires."""

    url: str
    recupere_le: datetime
    contenu_sha256: str
    mise_a_jour_source: datetime
    seance_fermee: bool
    lignes: tuple[LigneBruteCours, ...]

    @property
    def empreinte_tableau(self) -> str:
        """Empreinte stable du contenu utile (indépendante de l’horloge affichée)."""
        h = hashlib.sha256(self.mise_a_jour_source.isoformat().encode())
        for ligne in self.lignes:
            h.update(b"\x1e" + "\x1f".join(ligne.cellules).encode("utf-8"))
        return h.hexdigest()


class _ExtracteurTableaux(HTMLParser):
    """Extrait le texte de toutes les cellules de tous les tableaux HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tableaux: list[list[list[str]]] = []
        self._profondeur = 0
        self._ligne: list[str] | None = None
        self._cellule: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._profondeur += 1
            self.tableaux.append([])
        elif tag == "tr" and self._profondeur:
            self._ligne = []
        elif tag in {"td", "th"} and self._ligne is not None:
            self._cellule = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cellule is not None and self._ligne is not None:
            self._ligne.append(" ".join("".join(self._cellule).split()))
            self._cellule = None
        elif tag == "tr" and self._ligne is not None:
            if self._ligne:
                self.tableaux[-1].append(self._ligne)
            self._ligne = None
        elif tag == "table" and self._profondeur:
            self._profondeur -= 1

    def handle_data(self, data: str) -> None:
        if self._cellule is not None:
            self._cellule.append(data)


def analyser_date_mise_a_jour(html: str) -> datetime:
    """Lit la date « Dernière mise à jour » (heure locale BRVM, Africa/Abidjan)."""
    correspondance = _MOTIF_MISE_A_JOUR.search(html)
    if correspondance is None:
        raise ErreurCollecte("Date « Dernière mise à jour » introuvable sur la page BRVM.")
    jour, mois_texte, annee, heure, minute = correspondance.groups()
    mois = _MOIS.get(mois_texte.lower())
    if mois is None:
        raise ErreurCollecte("Mois de mise à jour BRVM non reconnu.")
    return datetime(int(annee), mois, int(jour), int(heure), int(minute), tzinfo=FUSEAU_BRVM)


def analyser_page_cours_actions(
    html: str,
    *,
    url: str = URL_COURS_ACTIONS,
    recupere_le: datetime | None = None,
    contenu: bytes | None = None,
) -> PageCoursActions:
    """Analyse le HTML; échoue si la structure attendue n’est pas présente."""
    extracteur = _ExtracteurTableaux()
    extracteur.feed(html)
    extracteur.close()

    tableau = next(
        (t for t in extracteur.tableaux if t and tuple(t[0]) == EN_TETE_ATTENDU),
        None,
    )
    if tableau is None:
        raise ErreurCollecte(
            "Tableau des cours BRVM introuvable : l’en-tête publié ne correspond plus "
            "au contrat attendu (structure du site modifiée ?)."
        )
    lignes = tuple(LigneBruteCours(tuple(cellules)) for cellules in tableau[1:])
    for ligne in lignes:
        if len(ligne.cellules) != len(EN_TETE_ATTENDU):
            raise ErreurCollecte("Ligne du tableau BRVM avec un nombre de colonnes inattendu.")
    if not lignes:
        raise ErreurCollecte("Le tableau des cours BRVM ne contient aucune ligne.")

    brut = contenu if contenu is not None else html.encode("utf-8")
    return PageCoursActions(
        url=url,
        recupere_le=recupere_le or datetime.now(UTC),
        contenu_sha256=hashlib.sha256(brut).hexdigest(),
        mise_a_jour_source=analyser_date_mise_a_jour(html),
        seance_fermee="seance-fermee" in html,
        lignes=lignes,
    )


def telecharger_page_cours_actions(
    *,
    url: str = URL_COURS_ACTIONS,
    nombre_max_tentatives: int = 3,
    delai_secondes: float = 10.0,
    timeout_secondes: float = 30.0,
) -> PageCoursActions:
    """Télécharge réellement la page BRVM (délai de 10 s entre essais, cf. robots.txt)."""
    derniere_erreur = "inconnue"
    for tentative in range(max(1, nombre_max_tentatives)):
        if tentative:
            time.sleep(delai_secondes)
        requete = urllib.request.Request(url, headers={"User-Agent": AGENT_UTILISATEUR})
        try:
            with urllib.request.urlopen(requete, timeout=timeout_secondes) as reponse:
                if reponse.status != 200:
                    derniere_erreur = f"HTTP {reponse.status}"
                    continue
                contenu: bytes = reponse.read()
                encodage = reponse.headers.get_content_charset() or "utf-8"
        except (urllib.error.URLError, TimeoutError, OSError) as erreur:
            derniere_erreur = type(erreur).__name__
            continue
        return analyser_page_cours_actions(
            contenu.decode(encodage, errors="strict"),
            url=url,
            recupere_le=datetime.now(UTC),
            contenu=contenu,
        )
    raise ErreurCollecte(f"Téléchargement de la page BRVM impossible ({derniere_erreur}).")
