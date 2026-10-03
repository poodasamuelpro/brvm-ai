# Collecteur n°1 — cours de fin de séance BRVM (site officiel)

**Statut : IMPLÉMENTÉ · TESTÉ EN RÉEL (téléchargement + insertion PostgreSQL locale avec les migrations du dépôt) · Supabase : À CONFIGURER (`BASE_DE_DONNEES_URL` absente de l’environnement d’exécution)**

## Source vérifiée (3 octobre 2026)

| Élément | Constat |
|---|---|
| URL | `https://www.brvm.org/fr/cours-actions/0` (HTTP 200, HTML public, sans authentification) |
| Contenu | Tableau « Symbole, Nom, Volume, Cours veille, Cours Ouverture, Cours Clôture, Variation (%) » — 48 actions le 02/10/2026 |
| Date de la donnée | Mention « Dernière mise à jour : Vendredi, 2 octobre, 2026 - 22:45 » + bandeau « Séance fermée » |
| Non publié | Plus haut, plus bas, valeur échangée → **non stockés** (jamais inventés) |
| Historique | **Non disponible** sur cette page (instantané de la dernière séance uniquement) ; l’historique BRVM est « sur demande » |
| robots.txt | `Crawl-delay: 10`, page non interdite ; conditions de réutilisation : **NON VÉRIFIÉ** (page mentions légales en 404) |
| Fréquence utile | 1 collecte par jour ouvré après la clôture (la page est mise à jour en soirée) |

Observation de qualité : la colonne « Cours veille » publiée ne correspond pas toujours à la variation publiée (ex. ABJC : veille 3 500, clôture 3 500, variation +3,86 %). Elle est conservée en brut mais **n’est pas utilisée** comme clôture précédente.

## Chaîne implémentée

`sources/donnees_marche.py` (téléchargement + extraction stricte de l’en-tête) → `validateurs.py` (types, symbole, nombres, volume, prix > 0, séance fermée, date non future et non week-end, doublons) → `pipeline.py` (une transaction) :

- `brvm.data_source` `BRVM_SITE_OFFICIEL`, `brvm.market` `BRVM` (XOF, Africa/Abidjan) ;
- `brvm.source_document` : URL, SHA-256 du HTML, `published_at` = mise à jour source ;
- `brvm.raw_ingest_record` : cellules brutes publiées, une ligne par valeur (`normalized` / `rejected`) ;
- `brvm.company`, `brvm.security`, `brvm.security_symbol_history` créés au premier symbole observé (`valid_from` = première séance observée, pays non déduit) ;
- `brvm.market_bar` (`1d`, ouverture/clôture/volume) ; volume nul → ouverture publiée « 0 » stockée NULL ;
- `brvm.data_quality_issue` pour rejets et quarantaines ; `brvm.pipeline_run` pour le suivi.

Idempotence : un instantané identique n’est pas réinséré ; une valeur différente pour une séance déjà validée est mise en `quarantined` (`revision_source`).

## Exécution

```bash
pip install -e ".[database]"
python scripts/lancer_pipeline.py --sec   # collecte + validation sans écriture
ACTIVER_BASE_DE_DONNEES=true BASE_DE_DONNEES_URL=... python scripts/lancer_pipeline.py
```
