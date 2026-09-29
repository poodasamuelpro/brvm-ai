# Schéma PostgreSQL — fondations

## Statut de cette étape

- **DÉVELOPPÉ** — migration Supabase initiale versionnée `20260929235900_initial_reference_and_provenance.sql`; schéma PostgreSQL `brvm`; référentiel relationnel de marchés, sociétés, titres et historique des symboles/secteurs; registre de sources et documents; contraintes, clés étrangères, index et suivi `updated_at`.
- **PRÉPARÉ** — colonnes de provenance et références d’objet Storage permettant de relier les futurs enregistrements à leur origine; tables futures détaillées dans les lots suivants.
- **À CONFIGURER DANS SUPABASE** — appliquer la migration dans le projet de l’utilisateur et décider de l’exposition API avant tout accès client.
- **NON IMPLÉMENTÉ** — collecte, fournisseur, jeu de référence BRVM, données de marché, stockage de documents, API, authentification et politiques RLS.

Cette migration ne contient **aucune donnée BRVM ou fournisseur préchargé**. Elle ne supprime ni ne renomme aucune table existante. Aucun projet Supabase distant n’a été modifié ni vérifié.

## Convention de migration

Les migrations SQL sont conservées dans `supabase/migrations/` avec un horodatage UTC et un nom descriptif. Elles constituent l’historique lisible et déployable par Supabase CLI. `supabase/config.toml` identifie seulement le projet local CLI; il ne contient ni référence de projet hébergé, ni clé, ni secret.

Ordre initial :

1. `20260929235900_initial_reference_and_provenance.sql` — crée `brvm` et les tables de référence/provenance.
2. Les migrations des lots ultérieurs s’exécuteront après cette migration et référenceront les clés définies ici.

Ne relance pas une migration déjà appliquée en copiant son contenu une seconde fois dans le même schéma. Pour une installation, exécuter chaque fichier une fois dans l’ordre. Pour une base existante, vérifier l’historique et l’état du schéma avant application; ne pas contourner une divergence en réexécutant manuellement.

### Déploiement manuel avec Supabase

Le projet distant n’est pas relié par cette tâche et aucune migration n’a été appliquée à distance. Pour la première installation manuelle :

1. Ouvrir le projet Supabase concerné, puis **SQL Editor**.
2. Créer une requête, coller le contenu complet du fichier de migration dans l’ordre, et vérifier que le projet/environnement sélectionné est le bon.
3. Exécuter une seule fois. Une erreur interrompt l’application; corriger la migration avant de poursuivre, plutôt que d’appliquer les lots suivants.
4. Vérifier la présence des tables dans le schéma `brvm` avec la requête ci-dessous.

```sql
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema = 'brvm'
ORDER BY table_name;
```

Pour des environnements récurrents, préférer Supabase CLI et l’historique `supabase_migrations.schema_migrations` afin de suivre les versions. Après liaison explicite du projet et configuration sécurisée de l’accès dans ton propre environnement, la commande documentée est `supabase db push`; elle n’a pas été exécutée par Manus.

## Objets créés par la migration

| Table/objet | Rôle | Intégrité et remarques |
|---|---|---|
| `brvm.country` | Référence pays | Code ISO alpha-2 formel, mais aucun code/nation seedé |
| `brvm.currency` | Référence devise | Code ISO alpha-3 formel, mais aucune devise seedée |
| `brvm.market` | Place ou marché | Références pays/devise facultatives tant que vérifiées; fuseau IANA optionnel |
| `brvm.sector` | Taxonomie sectorielle hiérarchique | Parent facultatif; aucune classification choisie arbitrairement |
| `brvm.company` | Identité d’émetteur | Nom légal requis; identifiants externes optionnels |
| `brvm.company_sector_history` | Appartenance sectorielle à validité temporelle | Date de début et fin inclusives; source documentaire prévue |
| `brvm.security` | Instrument financier rattaché à une société et un marché | ISIN optionnel et format contrôlé; dates de validité facultatives |
| `brvm.security_symbol_history` | Tickers/symboles successifs d’un titre | Historique par marché et dates, sans réécrire le passé |
| `brvm.data_source` | Registre de provenance | La source ne doit être enregistrée qu’après vérification et contrôle des droits d’usage |
| `brvm.source_document` | Document/artefact source et métadonnées d’acquisition | Identifiant, URL, empreinte SHA-256; clé Storage optionnelle, sans bucket créé |

Les clés primaires UUID utilisent `gen_random_uuid()`, intégré aux versions PostgreSQL modernes de Supabase; aucune extension n’est activée par cette migration. Les suppressions de données référencées sont en `RESTRICT`; les valeurs historiques ne disparaissent donc pas par cascade. Les périodes sont des dates de marché/comptables et les instants techniques sont `timestamptz`. Les dates de validité sont inclusives (`valid_to >= valid_from`).

Les clés étrangères, unicités et index soutiennent le modèle référentiel. Le partitionnement n’est pas introduit prématurément; les grosses séries temporelles seront évaluées avec des volumes et requêtes observés dans un lot ultérieur. Les horodatages `updated_at` des tables mutables sont actualisés par le trigger `brvm.touch_updated_at()`.

## Sécurité initiale

Les objets sont créés dans `brvm`, pas dans `public`. La migration n’accorde aucun privilège à `anon` ou `authenticated`, n’expose pas le schéma dans Supabase Data API et n’ajoute pas de policy permissive. N’expose pas le schéma avant la livraison et la revue du lot de sécurité/RLS. Ne place jamais une clé `service_role`, un mot de passe ou une URL de connexion réelle dans Git.

## Prochaine évolution

Les migrations suivantes ajouteront séparément les observations de marché, les faits fondamentaux, événements et validations qualité, puis les tables préparatoires d’analyses et d’exécutions. Ce premier lot ne rend opérationnelle aucune collecte, analyse, automatisation ni interface.


## Lot 2 — observations financières et qualité

- **DÉVELOPPÉ** — la migration `20260930000000_market_fundamentals_quality.sql` ajoute l’enregistrement brut par source, les barres de marché OHLCV, les sessions de calendrier, les périodes/faits fondamentaux, les opérations sur titres et anomalies qualité.
- **PRÉPARÉ** — la fréquence de barres est stockée comme code source en texte libre normalisé en minuscules; la base n’invente pas de fréquence quotidienne ou intrajournalière. Des révisions et sources concurrentes peuvent être conservées via les références d’ingestion.
- **NON IMPLÉMENTÉ** — aucune collecte, import, normalisation Python, validation automatique, calendrier officiel ou donnée BRVM n’est fourni dans ce lot.

### Modèle ajouté

`raw_ingest_record` garde la structure reçue et son statut de traitement. `market_bar`, `financial_fact`, `market_calendar_session` et `corporate_action` sont les représentations normalisées et rattachent chaque fait à son `data_source` et à un `raw_ingest_record`. Une clé de document source est accessible par cette chaîne de provenance. Les valeurs de prix, volumes et montants sont `numeric` à précision explicite; les compteurs de transactions sont entiers. Les contraintes valident l’ordre OHLC, les valeurs positives/non négatives, les dates, périodes et rapports de split lorsqu’ils existent.

`financial_period` rattache les faits comptables à une société et à une période. Chaque fait porte un `metric_code`, unité, devise éventuelle, date de publication et date de disponibilité. Si `available_at` est inconnu, il reste `NULL` : une analyse point-in-time doit exclure ces faits ou signaler cette limite, jamais supposer qu’ils étaient connus à la clôture de période. `market_date` est la date locale du marché fournie par la source/calendrier, tandis que les heures techniques sont conservées en `timestamptz`.

`data_quality_issue` localise un seul enregistrement brut, cours, fait fondamental ou corporate action par clé étrangère réelle. Il conserve code de règle, gravité, état et contexte JSONB borné; ce contexte ne doit contenir ni secrets, ni payload complet, ni valeurs sensibles inutiles. L’état qualité des enregistrements et les anomalies sont des champs de persistance, pas un validateur exécuté automatiquement.

### Déploiement des migrations

Pour une base encore vierge, appliquer **dans l’ordre** `20260929235900_initial_reference_and_provenance.sql`, puis `20260930000000_market_fundamentals_quality.sql`. Pour mettre à jour une base où le lot 1 est déjà installé, n’exécuter que la seconde migration après confirmation de son historique. Aucun changement Supabase n’a été exécuté à distance.


## Lot 3 — analyses, rétro-tests, ML et signaux

- **DÉVELOPPÉ** — migration `20260930001000_analytics_models_backtests_signals.sql` : traçabilité de calcul, définitions et résultats versionnés d’indicateurs, résultats d’analyse reliés à des entrées sources, stratégies et versions, exécutions de rétro-tests, instruments/trades/métriques, versions de jeux de données et définitions de features/labels, échantillons, modèles/version, évaluations, prédictions/outcomes et signaux/facteurs explicatifs.
- **PRÉPARÉ** — `calculation_run` conserve code_version, paramètres, cutoff `as_of`, empreinte d’entrée, statuts et erreurs non secrètes pour permettre la reproduction. Les liens d’entrée et de facteurs pointent aux cours, faits, opérations ou enregistrements bruts via clés étrangères.
- **NON IMPLÉMENTÉ** — aucun indicateur SQL, algorithme de stratégie, simulation, pipeline d’entraînement, modèle, prédiction ou signal n’est exécuté par ces tables. Aucune définition ou donnée de modèle n’est seedée.

Les définitions d’indicateurs et de stratégies ont des versions distinctes; modifier une formule implique d’enregistrer une nouvelle version plutôt que de réécrire les résultats passés. Les paramètres/hyperparamètres JSONB sont contraints à des objets. Les échantillons ML séparent les splits `train`, `validation`, `test` et `inference`; leurs features/labels conservent la représentation utile à la version du dataset. `sample_available_at` postérieur à l’instant de l’observation est rejeté pour éviter une fuite temporelle. L’appelant reste responsable de construire un dataset point-in-time sans survivorship bias.

Les sorties utilisent des tables spécialisées avec relations typées lorsque le domaine est connu. Les tables de traces ont des clés étrangères vers les données réellement connues; aucune intégration d’un fournisseur ou d’un framework ML n’est supposée. Les URI d’artefacts restent facultatives et ne constituent pas une intégration Storage.

### Ordre de déploiement à ce stade

Sur une base vierge, appliquer les migrations `20260929235900_initial_reference_and_provenance.sql`, `20260930000000_market_fundamentals_quality.sql`, puis `20260930001000_analytics_models_backtests_signals.sql`. Si les deux premières sont déjà installées, appliquer uniquement la troisième après confirmation de leur historique.
