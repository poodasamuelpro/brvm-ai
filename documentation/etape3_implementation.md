# Étape 3 — Implémentation actuelle

Ce document décrit uniquement les fonctionnalités effectivement présentes dans le dépôt.
Une fonctionnalité codée n'est pas déclarée opérationnelle sans exécution réelle vérifiée.

## Lots livrés

### Lot 1 — Correspondances multi-sources

Le registre `brvm.security_external_identifier` conserve le ticker fournisseur,
le titre BRVM, la source, la référence justificative, le statut de vérification et
la période de validité. L'import SIKA ne déduit plus un titre à partir du nom du ticker.

Pour une nouvelle correspondance explicite :

```bash
python scripts/lancer_historique_sika.py \
  --ticker SNTS.sn \
  --mapping SNTS.sn=SNTS \
  --debut 2026-07-01 \
  --fin 2026-10-02
```

Une correspondance déjà enregistrée et `verified` peut être réutilisée sans `--mapping`.
Une correspondance absente ou `rejected` bloque l'import.

### Lot 2 — Collecte quotidienne BRVM

Le workflow `.github/workflows/collecte-brvm-quotidienne.yml` lance le collecteur
officiel du lundi au vendredi à 18:30 UTC et peut être déclenché manuellement.
Il utilise uniquement le secret GitHub `BRVM_DATABASE_URL` et ne contient aucune clé.

La création du workflow ne constitue pas une preuve d'exécution opérationnelle tant
qu'une exécution GitHub Actions réelle n'a pas été vérifiée.

### Lot 3 — Dividendes et opérations sur titres

Le script `scripts/importer_evenements.py` accepte un JSON fourni par une source
vérifiée et conserve le payload original dans `brvm.raw_ingest_record`. Les événements
sont enregistrés dans la table existante `brvm.corporate_action`.

Les types d'événements peuvent inclure les dividendes, fractionnements, regroupements,
augmentations ou réductions de capital. Les dates d'annonce, de détachement,
d'enregistrement, d'effet et de paiement sont stockées séparément lorsqu'elles sont
publiées. Les événements restent `pending` par défaut.

### Lot 4 — Fondamentaux

Le script `scripts/importer_fondamentaux.py` ingère des faits financiers structurés
sans mélanger les périodes ni les périmètres. Chaque fait porte :

- la société résolue par symbole BRVM ;
- le début et la fin de période ;
- le type de période ;
- le périmètre social ou consolidé ;
- le code métrique ;
- la valeur et l'unité ;
- la devise lorsqu'elle est connue ;
- la publication et la disponibilité lorsqu'elles sont connues ;
- le statut de validation.

Les faits sont conservés dans `brvm.financial_period` et `brvm.financial_fact`, avec
le document et le payload source.

### Lot 5 — BCEAO/UEMOA

La migration `20261101001000_macro_observations.sql` ajoute `brvm.macro_observation`.
Le script `scripts/importer_macro.py` sépare la période statistique de la date de
publication, conserve la zone ou le pays, la valeur, l'unité et la provenance.

Aucune valeur BCEAO n'est ajoutée automatiquement par le dépôt.

### Lot 6 — Divergences multi-sources

`src/brvm_ia/collecte/consolidation.py` compare les observations validées pour un
titre et une séance. La source `BRVM` est prioritaire lorsqu'elle existe. Une source
secondaire ne remplace jamais l'observation officielle. Les divergences sont consignées
dans `brvm.data_quality_issue` avec le code `multi_source_divergence`.

Commande :

```bash
python scripts/reconcilier_cours.py \
  --security-id UUID \
  --date 2026-10-08
```

## Limites non masquées

- SIKA reste un endpoint web non documenté et peut répondre HTTP 403 ; sa collecte
  quotidienne n'est pas déclarée opérationnelle.
- Les sources de rapports, fondamentaux et BCEAO doivent fournir un JSON issu d'une
  publication vérifiée ; aucune donnée réelle n'est inventée dans le dépôt.
- Le workflow BRVM est codé, mais son exécution GitHub Actions et son écriture Supabase
  doivent être vérifiées séparément.
- Les faits ambigus restent `pending` et ne doivent pas alimenter les analyses validées.
- Les lots ne développent ni IA, ni signaux, ni frontend, conformément au périmètre de
  l'étape 3.
