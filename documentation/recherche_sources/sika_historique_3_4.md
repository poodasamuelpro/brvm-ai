# Étape 3.4 — Historique SIKA Finance

## Sources testées

| Méthode | Résultat vérifié | Décision |
|---|---|---|
| Endpoint `POST /api/general/GetHistos` | HTTP 403 depuis l’exécution Python et HTTP 403 depuis le navigateur Sandbox lors du test du 03/10/2026 | Aucun contournement. Le collecteur remonte une indisponibilité explicite et tente uniquement la page publique. |
| Page publique `https://www.sikafinance.com/marches/historiques/SNTS.sn` | La page a affiché un tableau historique réel pour SONATEL (`SNTS.sn`), avec 64 lignes du 07/07/2026 au 02/10/2026 | Méthode de repli légitime, avec parsing strict de l’en-tête et des colonnes. |
| CSV SIKA | Aucun lien CSV ni fichier CSV exploitable n’a pu être récupéré et vérifié dans l’accès public testé ; la page a ensuite été bloquée par Cloudflare | NON ACCESSIBLE / NON VÉRIFIÉ. Aucun endpoint CSV n’est inventé. |

## Données réellement récupérées

- Ticker SIKA : `SNTS.sn`.
- Correspondance vérifiée en base : `SNTS` / SONATEL.
- Période : 07/07/2026 → 02/10/2026.
- Nombre de lignes : 64 séances.
- Champs : date, ouverture, plus haut, plus bas, clôture, volume titres, volume FCFA, variation.
- Exemple vérifié le 02/10/2026 : clôture 45 000, volume 36 615, volume FCFA 1 647 675 000.

## Supabase réel

Les données ont été écrites dans les tables existantes du schéma `brvm`, sans migration ni table nouvelle :

- `brvm.data_source` : source `SIKA_FINANCE` ;
- `brvm.source_document` : URL, identifiant externe, empreinte et date de collecte ;
- `brvm.raw_ingest_record` : 64 lignes brutes ;
- `brvm.market_bar` : 64 barres OHLCV `validated` ;
- `brvm.pipeline_definition` ;
- `brvm.pipeline_run` ;
- `brvm.pipeline_run_source`.

Contrôles réels :

- connexion Python → Supabase : `SELECT 1` OK ;
- schéma `brvm` présent ;
- 56 tables existantes ;
- 64 dates distinctes ;
- 0 doublon sur `(security_id, source_id, market_date, interval_code)` ;
- seconde exécution de l’import capturé : 0 insertion grâce à l’identifiant du document source.

## Implémentation

- `src/brvm_ia/collecte/sources/sika_finance.py` : endpoint JSON, page publique, validation OHLCV, `nodata`, HTTP 401/403/404, HTML inattendu et doublons.
- `scripts/lancer_historique_sika.py` : collecte, validation, provenance, écriture transactionnelle dans les tables `brvm` et déduplication.
- `tests/collecte/test_sika_finance.py` : tests du JSON, OHLC, doublons et tableau HTML public.

## Automatisation

- Prête pour production : **NON**.
- Motif : le point automatisé et la page sont actuellement bloqués par Cloudflare dans l’environnement d’exécution Python.
- Workflow GitHub Actions ajouté : **NON**, volontairement. Le document exige de ne pas mettre en production une automatisation reposant sur une méthode SIKA non vérifiée.
- Une fois un accès public automatisable vérifié, le script pourra être planifié avec `BASE_DE_DONNEES_URL` comme secret GitHub, sans secret dans le dépôt ni les logs.

## Limites

- Le CSV n’est pas déclaré accessible, car aucun fichier n’a été récupéré et inspecté.
- Les autres tickers (`ABJC`, `ORAC`, `BBGC`, `NTLC`, `SEMC`) n’ont pas été enregistrés dans Supabase dans cette tâche sans récupération et correspondance vérifiées individuellement.
- Aucune valeur absente n’a été inventée.
