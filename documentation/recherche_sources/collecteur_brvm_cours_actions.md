# Collecteur n°1 — cours de fin de séance BRVM (site officiel)

**Statut : IMPLÉMENTÉ · TESTÉ EN RÉEL · STOCKÉ DANS SUPABASE (séance du 02/10/2026, 48 valeurs, collecte du 03/10/2026)**

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

Codes de sortie : `0` succès (y compris séance déjà collectée), `2` séance non fermée (rien n’est écrit), `1` échec.

## Fonctionnement opérationnel

| Cas | Comportement |
|---|---|
| Nouvelle séance fermée | Insertion complète dans une transaction, `pipeline_run` = `succeeded` |
| Relance / week-end / férié (page inchangée) | Aucune donnée réécrite ; `pipeline_run` `succeeded` avec 0 insertion (traçabilité de l’exécution) |
| Séance en cours | Refus (`exit 2`) : aucun cours provisoire stocké |
| Structure HTML modifiée, réseau, base | `exit 1`, transaction annulée, échec tracé dans `pipeline_run` (`failed`) + `pipeline_run_error` |
| Valeur révisée pour une séance déjà validée | Nouvelle barre `quarantined` + constat `revision_source`, l’ancienne est conservée |

Reprise après erreur : la transaction étant atomique, une relance suffit ; l’idempotence empêche les doublons.

## Vérification Supabase (03/10/2026)

- Connexion Python → Supabase : `SELECT 1` OK ; schéma `brvm` présent (56 tables), colonnes identiques aux migrations du dépôt ; aucune migration rejouée.
- Exécution 1 : 48 `market_bar` `validated`, 48 `raw_ingest_record`, 1 `source_document`, 48 titres/sociétés/symboles.
- Exécution 2 : `deja_collecte=True`, 0 insertion → 48 barres pour 48 couples (titre, séance, source) : aucun doublon.

## Plan des lots restants de l’étape 3

1. **3.3 (fait)** — Supabase réel + collecte BRVM opérationnelle.
2. **3.4** — Historique SIKA Finance (`POST /api/general/GetHistos`, non documenté ; 66 séances SNTS 03/07→02/10/2026 vérifiées), découverte des tickers, identifiants par source.
3. **3.5** — Identification multi-sources (correspondances BRVM ↔ SIKA vérifiées, ISIN) et règle de divergence entre sources.
4. **3.6** — Indices et capitalisation BRVM (page officielle).
5. **3.7** — Dividendes / opérations sur titres (sources officielles BRVM/émetteurs).
6. **3.8** — Fondamentaux (rapports BRVM / émetteurs, extraction contrôlée).
7. **3.9** — BCEAO (séries macro : taux directeurs, inflation, agrégats).
8. **3.10** — Automatisation quotidienne GitHub Actions (secret `BASE_DE_DONNEES_URL`) et bilan Bloomberg (NON ACCESSIBLE sans licence).
