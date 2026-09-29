BRVM-AI

Intelligence financière et analyse quantitative dédiée à la BRVM

BRVM-AI est une plateforme d'analyse financière et quantitative dédiée à la Bourse Régionale des Valeurs Mobilières (BRVM) et, plus largement, à l'écosystème financier de l'UEMOA.

Le projet combine :

- données de marché ;
- données financières des entreprises ;
- analyse fondamentale ;
- analyse technique ;
- valorisation ;
- analyse des risques ;
- statistiques ;
- apprentissage automatique ;
- rétro-tests de stratégies ;
- génération de signaux ;
- analyse et suivi historiques ;
- automatisation des traitements.

L'objectif est de construire progressivement un système capable de transformer des données financières brutes en analyses structurées, signaux explicables et informations exploitables.

«BRVM-AI n'est pas conçu comme un système garantissant des gains. Les modèles, scores et signaux sont des résultats analytiques soumis aux limites des données, des modèles et des conditions de marché.»

---

1. Vision du projet

Les marchés financiers produisent une quantité importante de données, mais ces données doivent être :

1. collectées ;
2. nettoyées ;
3. validées ;
4. historisées ;
5. transformées ;
6. analysées ;
7. comparées ;
8. modélisées ;
9. évaluées ;
10. présentées de manière compréhensible.

BRVM-AI cherche à construire cette chaîne de manière structurée pour le marché de la BRVM.

Le système doit progressivement permettre de répondre à des questions telles que :

- Quelle est la situation actuelle d'une valeur ?
- Comment son cours a-t-il évolué ?
- Comment ses fondamentaux évoluent-ils ?
- Quelle est sa valorisation ?
- Quelle est sa volatilité ?
- Quelle est sa liquidité ?
- Comment se comporte son secteur ?
- Quels facteurs expliquent son évolution ?
- Quels signaux techniques sont présents ?
- Quels facteurs fondamentaux sont favorables ou défavorables ?
- Comment une stratégie aurait-elle fonctionné historiquement ?
- Quel est le niveau de risque associé ?
- Comment plusieurs valeurs se comparent-elles ?
- Quelles observations ressortent des données historiques ?

---

2. Objectifs

2.1 Objectifs principaux

BRVM-AI vise à :

- centraliser les données relatives aux valeurs BRVM ;
- conserver un historique exploitable ;
- automatiser la collecte des données ;
- automatiser le nettoyage et la validation ;
- calculer des indicateurs financiers ;
- effectuer des analyses quantitatives ;
- construire des modèles statistiques et d'apprentissage automatique ;
- tester les stratégies sur des données historiques ;
- générer des signaux explicables ;
- suivre les performances des modèles ;
- fournir une interface d'analyse claire.

---

3. Principe fondamental

Le projet suit une architecture data-first.

La donnée brute ne doit pas être directement utilisée par les modèles.

Le pipeline général est :

Sources de données
        │
        ▼
Collecte
        │
        ▼
Validation
        │
        ▼
Nettoyage
        │
        ▼
Base de données historique
        │
        ├───────────────┐
        ▼               ▼
Indicateurs        Données financières
        │               │
        └───────┬───────┘
                ▼
             Analyses
                │
        ┌───────┴────────┐
        ▼                ▼
     Modèles IA      Rétro-tests
        │                │
        └───────┬────────┘
                ▼
             Signaux
                │
                ▼
          Explications
                │
                ▼
            Interface

---

4. Fonctionnement général

Étape 1 — Collecte

Le système récupère les informations disponibles auprès de sources autorisées et exploitables.

Les catégories de données peuvent inclure :

- cours ;
- volumes ;
- transactions disponibles ;
- indices ;
- capitalisation ;
- résultats financiers ;
- états financiers ;
- dividendes ;
- informations sur les entreprises ;
- informations sectorielles ;
- actualités ;
- données macroéconomiques pertinentes.

---

Étape 2 — Validation

Chaque donnée collectée doit être contrôlée avant son insertion dans la base.

Exemples de contrôles :

- valeur manquante ;
- doublon ;
- date incorrecte ;
- cours négatif ou impossible ;
- volume incohérent ;
- variation anormale ;
- entreprise inconnue ;
- source indisponible ;
- format inattendu.

---

Étape 3 — Nettoyage

Les données sont ensuite normalisées.

Exemples :

- formats de dates ;
- noms d'entreprises ;
- identifiants ;
- devises ;
- unités ;
- valeurs manquantes ;
- doublons ;
- données aberrantes ;
- séries temporelles.

---

5. Historisation

L'historique constitue un élément central du projet.

BRVM-AI doit conserver les données historiques afin de permettre :

- analyses temporelles ;
- comparaison de périodes ;
- calculs de rendement ;
- volatilité ;
- corrélations ;
- études sectorielles ;
- entraînement des modèles ;
- rétro-tests ;
- comparaison de stratégies.

Les nouvelles données ne doivent pas écraser inutilement les anciennes.

Le système doit privilégier une logique d'append/update contrôlée.

---

6. Analyse technique

Le module d'analyse technique permet de calculer différents indicateurs à partir des séries de marché.

Exemples :

- moyennes mobiles ;
- RSI ;
- MACD ;
- bandes de Bollinger ;
- momentum ;
- variations ;
- rendements ;
- volatilité ;
- drawdown ;
- supports et résistances ;
- volumes ;
- indicateurs de tendance.

Les indicateurs doivent être calculés à partir des données historiques disponibles.

---

7. Analyse fondamentale

L'analyse fondamentale cherche à étudier la situation financière et économique des entreprises.

Les données potentielles comprennent notamment :

- chiffre d'affaires ;
- résultat net ;
- résultat opérationnel ;
- bénéfice par action ;
- capitaux propres ;
- dette ;
- trésorerie ;
- flux de trésorerie ;
- marges ;
- rentabilité ;
- croissance ;
- dividendes.

Les indicateurs peuvent notamment inclure :

- PER ;
- P/B ;
- rendement du dividende ;
- ROE ;
- ROA ;
- marges ;
- croissance du chiffre d'affaires ;
- croissance du résultat ;
- ratios d'endettement ;
- ratios de liquidité.

Les indicateurs réellement calculables dépendent de la disponibilité et de la qualité des données.

---

8. Valorisation

BRVM-AI pourra intégrer plusieurs méthodes de valorisation.

Exemples :

Méthodes relatives

- PER ;
- P/B ;
- EV/EBITDA ;
- rendement du dividende ;
- comparables sectoriels.

Méthodes intrinsèques

- DCF ;
- actualisation des flux ;
- modèles de dividendes lorsque les données le permettent.

La valorisation doit toujours conserver les hypothèses utilisées.

Exemple :

Entreprise
    │
    ├── Hypothèses
    ├── Données historiques
    ├── Prévisions
    ├── Taux d'actualisation
    ├── Scénario central
    ├── Scénario optimiste
    └── Scénario prudent

---

9. Analyse des risques

Le système doit également mesurer différents risques.

Exemples :

- volatilité ;
- drawdown ;
- risque de liquidité ;
- concentration ;
- exposition sectorielle ;
- corrélation ;
- variation extrême ;
- risque de modèle.

Les mesures utilisées doivent être conservées avec leur méthodologie.

---

10. Intelligence artificielle

L'IA n'est pas utilisée comme une boîte noire produisant simplement une réponse.

Le projet privilégie une approche combinant :

Données
   +
Indicateurs
   +
Statistiques
   +
Modèles ML
   +
Rétro-tests
   +
Explications

---

11. Machine Learning

Les modèles envisagés comprennent notamment :

- régression ;
- classification ;
- Random Forest ;
- Gradient Boosting ;
- XGBoost ;
- LightGBM ;
- modèles statistiques.

L'utilisation de modèles plus complexes, notamment de deep learning, pourra être envisagée ultérieurement si :

- la quantité de données est suffisante ;
- la qualité des données est suffisante ;
- le modèle apporte une amélioration mesurable ;
- le risque de surapprentissage est maîtrisé.

---

12. Prévision

Les modèles pourront être utilisés pour différentes tâches.

Exemples :

Classification

Hausse
Stable
Baisse

Score

Score technique
Score fondamental
Score risque
Score valorisation
Score global

Prévision

Le système peut également estimer certaines variables futures selon le modèle utilisé.

Toute prévision doit être accompagnée de :

- période ;
- modèle ;
- données utilisées ;
- métriques d'évaluation ;
- incertitude lorsque disponible ;
- date de génération.

---

13. Signaux

Le module "signaux/" transforme les résultats analytiques en informations compréhensibles.

Exemple conceptuel :

Valeur : ABC

Analyse technique       : favorable
Analyse fondamentale    : neutre
Valorisation            : favorable
Risque                  : modéré
Momentum                : favorable
Liquidité               : faible

Signal analytique       : FAVORABLE

Le système doit également expliquer les facteurs ayant contribué au signal.

Exemple :

Facteurs favorables :
+ amélioration du momentum
+ valorisation inférieure à certains comparables

Facteurs défavorables :
- liquidité faible
- volatilité élevée

Les signaux ne constituent pas une garantie de performance future.

---

14. Rétro-tests

Les stratégies doivent être testées sur des données historiques avant d'être considérées comme exploitables.

Le moteur de rétro-test doit prendre en compte :

- capital initial ;
- dates ;
- achats ;
- ventes ;
- frais ;
- liquidité ;
- contraintes de marché disponibles ;
- portefeuille ;
- rendement ;
- volatilité ;
- drawdown ;
- ratio de Sharpe lorsque pertinent ;
- nombre de transactions ;
- taux de réussite ;
- autres métriques pertinentes.

Exemple :

Capital initial
      │
      ▼
Données historiques
      │
      ▼
Stratégie
      │
      ▼
Transactions simulées
      │
      ▼
Frais
      │
      ▼
Portefeuille simulé
      │
      ▼
Performance

---

15. Prévention du surapprentissage

Le projet doit éviter de considérer qu'un modèle est performant uniquement parce qu'il fonctionne sur les données utilisées pour son entraînement.

Les tests doivent distinguer autant que possible :

Données d'entraînement
        │
        ▼
Entraînement
        │
        ▼
Validation
        │
        ▼
Test hors échantillon
        │
        ▼
Rétro-test

Les données futures ne doivent pas être utilisées accidentellement dans le calcul des variables historiques.

Une attention particulière doit être portée au data leakage.

---

16. Base de données

La base principale prévue est :

PostgreSQL

Elle doit permettre de conserver :

- entreprises ;
- secteurs ;
- cours ;
- volumes ;
- indices ;
- états financiers ;
- dividendes ;
- indicateurs ;
- analyses ;
- prédictions ;
- modèles ;
- signaux ;
- résultats de rétro-tests ;
- métadonnées ;
- sources.

Extension vectorielle

Lorsque nécessaire, pgvector pourra être utilisé directement dans PostgreSQL afin d'éviter l'ajout prématuré d'une base vectorielle séparée.

---

17. Architecture technique

Frontend

Next.js
TypeScript
Tailwind CSS
shadcn/ui

Visualisation

Lightweight Charts
ou
Apache ECharts

Backend

Python
FastAPI

Data Science

Python
Pandas
Polars
NumPy
SciPy
statsmodels

Machine Learning

scikit-learn
XGBoost
LightGBM

Base de données

PostgreSQL
pgvector

Automatisation

GitHub Actions

Infrastructure complémentaire

Selon les besoins :

Cloudflare Workers
Redis
MLflow
Prometheus
Grafana

Ces composants ne sont pas tous nécessaires au démarrage.

---

18. Stack complète

Domaine| Technologie
Langage principal data/IA| Python
API| FastAPI
Frontend| Next.js
Langage frontend| TypeScript
UI| Tailwind CSS + shadcn/ui
Graphiques| Lightweight Charts / ECharts
DataFrame| Pandas / Polars
Calcul scientifique| NumPy / SciPy
Statistiques| statsmodels
ML| scikit-learn
Boosting| XGBoost / LightGBM
Backtesting| moteur interne + bibliothèque spécialisée si nécessaire
Base de données| PostgreSQL
Vectorisation| pgvector
Automatisation| GitHub Actions
Dépôt| GitHub
API edge éventuelle| Cloudflare Workers
Cache éventuel| Redis
Suivi ML éventuel| MLflow
Monitoring éventuel| Prometheus / Grafana

---

19. Architecture du dépôt

brvm-ai/
│
├── .github/
│   └── workflows/
│       ├── pipeline_quotidien.yml
│       ├── pipeline_hebdomadaire.yml
│       └── tests.yml
│
├── src/
│   └── brvm_ia/
│       ├── __init__.py
│       │
│       ├── configuration/
│       │   ├── __init__.py
│       │   └── parametres.py
│       │
│       ├── collecte/
│       │   ├── __init__.py
│       │   ├── sources/
│       │   │   ├── __init__.py
│       │   │   ├── donnees_marche.py
│       │   │   ├── donnees_financieres.py
│       │   │   ├── dividendes.py
│       │   │   └── actualites.py
│       │   ├── validateurs.py
│       │   └── pipeline.py
│       │
│       ├── base_de_donnees/
│       │   ├── __init__.py
│       │   ├── connexion.py
│       │   ├── modeles.py
│       │   ├── depots.py
│       │   └── migrations/
│       │
│       ├── nettoyage/
│       │   ├── __init__.py
│       │   ├── cours.py
│       │   ├── finances.py
│       │   └── validation.py
│       │
│       ├── indicateurs/
│       │   ├── __init__.py
│       │   ├── techniques.py
│       │   ├── fondamentaux.py
│       │   ├── valorisation.py
│       │   ├── volatilite.py
│       │   └── liquidite.py
│       │
│       ├── analyses/
│       │   ├── __init__.py
│       │   ├── marche.py
│       │   ├── entreprises.py
│       │   ├── secteurs.py
│       │   └── risques.py
│       │
│       ├── modeles_ia/
│       │   ├── __init__.py
│       │   ├── jeux_donnees.py
│       │   ├── entrainement.py
│       │   ├── predictions.py
│       │   ├── evaluation.py
│       │   └── registre.py
│       │
│       ├── retro_tests/
│       │   ├── __init__.py
│       │   ├── moteur.py
│       │   ├── strategies.py
│       │   ├── couts.py
│       │   ├── indicateurs_performance.py
│       │   └── rapports.py
│       │
│       ├── signaux/
│       │   ├── __init__.py
│       │   ├── notation.py
│       │   ├── regles.py
│       │   └── explications.py
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── application.py
│       │   └── routes/
│       │       ├── marche.py
│       │       ├── entreprises.py
│       │       ├── analyses.py
│       │       └── signaux.py
│       │
│       └── taches/
│           ├── quotidien.py
│           ├── hebdomadaire.py
│           └── reconstruire_indicateurs.py
│
├── tests/
│   ├── collecte/
│   ├── nettoyage/
│   ├── indicateurs/
│   ├── analyses/
│   ├── modeles_ia/
│   ├── retro_tests/
│   └── api/
│
├── scripts/
│   ├── initialiser_base.py
│   ├── importer_historique.py
│   └── lancer_pipeline.py
│
├── cahiers/
│   ├── exploration/
│   └── recherche/
│
├── documentation/
│   ├── architecture.md
│   ├── sources_donnees.md
│   ├── base_donnees.md
│   └── methodologie.md
│
├── interface/
│   └── README.md
│
├── .env.exemple
├── .gitignore
├── pyproject.toml
├── README.md
└── LICENCE

---

20. Automatisation

Le projet utilise GitHub Actions pour automatiser certaines tâches.

Pipeline quotidien

Déclenchement programmé
        │
        ▼
Collecte
        │
        ▼
Validation
        │
        ▼
Nettoyage
        │
        ▼
Insertion PostgreSQL
        │
        ▼
Calcul indicateurs
        │
        ▼
Analyse
        │
        ▼
Prédictions
        │
        ▼
Signaux
        │
        ▼
Rapport

Pipeline hebdomadaire

Il peut notamment effectuer :

- réentraînement des modèles ;
- validation des modèles ;
- rétro-tests ;
- comparaison des performances ;
- recalcul complet des indicateurs ;
- rapports de qualité des données.

---

21. Persistance des données

GitHub Actions n'est pas utilisé comme base de données.

Il sert uniquement à exécuter les traitements.

La persistance doit être assurée par PostgreSQL.

GitHub Actions
      │
      │ exécute
      ▼
Python
      │
      │ lit / écrit
      ▼
PostgreSQL
      │
      ▼
Historique permanent

Cette architecture permet de conserver les données sur :

- plusieurs jours ;
- semaines ;
- mois ;
- années ;

selon la qualité et la disponibilité des données collectées.

---

22. Fréquence des données

La fréquence réelle des analyses dépend de la fréquence des données disponibles.

Données quotidiennes

Adaptées à :

- analyse de clôture ;
- indicateurs journaliers ;
- stratégies moyen/long terme ;
- analyse fondamentale ;
- réentraînement périodique.

Données intraday

Elles nécessitent une source fournissant réellement des données intraday suffisamment fiables.

BRVM-AI ne doit pas simuler une précision intraday à partir de données quotidiennes.

---

23. Gestion des sources

Chaque donnée importante devrait idéalement conserver sa provenance.

Exemple conceptuel :

Donnée
 ├── source
 ├── date_collecte
 ├── date_donnée
 ├── type_source
 └── statut_validation

Cela facilite :

- l'audit ;
- la correction ;
- la traçabilité ;
- la comparaison des sources.

---

24. Sécurité

Les informations sensibles ne doivent jamais être stockées directement dans le code.

Exemples :

DATABASE_URL
API_KEY
SECRET_KEY
TOKEN
PASSWORD

doivent être stockés dans des variables d'environnement ou des secrets GitHub.

Le fichier :

.env

ne doit jamais être versionné.

Le fichier :

.env.exemple

sert uniquement de modèle.

---

25. Confidentialité

Le projet peut être utilisé comme outil personnel ou privé.

L'interface peut être protégée par authentification.

L'API ne doit pas être exposée publiquement sans mécanisme de sécurité approprié.

La base PostgreSQL ne doit pas être directement exposée au navigateur.

Architecture recommandée :

Utilisateur
     │
     ▼
Frontend
     │
     ▼
API sécurisée
     │
     ▼
PostgreSQL

---

26. API

L'API FastAPI permet de séparer l'interface utilisateur des traitements financiers.

Exemples d'endpoints prévus :

GET /marche
GET /marche/indices
GET /entreprises
GET /entreprises/{id}
GET /analyses
GET /analyses/{id}
GET /signaux
GET /signaux/{id}

Les endpoints exacts pourront évoluer avec l'implémentation.

---

27. Qualité des données

La qualité des données est prioritaire sur la complexité des modèles.

Un modèle complexe entraîné sur de mauvaises données produit des résultats peu fiables.

Priorité :

Qualité des données
        >
Qualité des indicateurs
        >
Qualité des rétro-tests
        >
Qualité du modèle
        >
Complexité du modèle

---

28. Tests

Chaque module doit progressivement disposer de tests automatisés.

Les tests couvrent notamment :

- collecte ;
- validation ;
- nettoyage ;
- indicateurs ;
- analyses ;
- modèles ;
- rétro-tests ;
- API.

Exemple :

pytest

---

29. Environnement de développement

Pré-requis principaux :

- Python ;
- Git ;
- GitHub ;
- PostgreSQL ;
- environnement virtuel Python.

Création de l'environnement :

python -m venv .venv

Activation sous Windows :

.venv\Scripts\Activate.ps1

Activation sous Linux/macOS :

source .venv/bin/activate

Installation des dépendances :

pip install -e .

---

30. Configuration

Créer un fichier :

.env

à partir de :

.env.exemple

Exemple conceptuel :

DATABASE_URL=
SECRET_KEY=
API_KEY=

Les valeurs réelles ne doivent jamais être publiées dans Git.

---

31. Lancement local

API :

uvicorn brvm_ia.api.application:app --reload

Pipeline :

python scripts/lancer_pipeline.py

Import historique :

python scripts/importer_historique.py

Initialisation :

python scripts/initialiser_base.py

---

32. Philosophie de développement

BRVM-AI privilégie :

- simplicité ;
- modularité ;
- reproductibilité ;
- traçabilité ;
- qualité des données ;
- tests ;
- documentation ;
- sécurité ;
- évolutivité.

Le projet évite les composants lourds lorsqu'ils n'apportent pas de bénéfice réel.

---

33. Ce qui n'est pas nécessaire au démarrage

Les technologies suivantes ne sont pas prioritaires pour la première version :

- Kubernetes ;
- Kafka ;
- architecture microservices complexe ;
- cluster GPU ;
- deep learning massif ;
- base vectorielle séparée ;
- Redis obligatoire ;
- MLflow obligatoire ;
- Docker obligatoire.

Elles pourront être ajoutées si les besoins réels du projet le justifient.

---

34. Évolution possible

Architecture cible progressive :

                    ┌──────────────────┐
                    │ Sources BRVM     │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Collecte Python  │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Validation       │
                    │ Nettoyage        │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ PostgreSQL       │
                    │ + pgvector       │
                    └────────┬─────────┘
                             │
             ┌───────────────┼───────────────┐
             ▼               ▼               ▼
       Fondamentaux     Technique        Actualités
             │               │               │
             └───────────────┼───────────────┘
                             ▼
                    ┌──────────────────┐
                    │ Analyse          │
                    └────────┬─────────┘
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
               Modèles IA        Rétro-tests
                    │                 │
                    └────────┬────────┘
                             ▼
                    ┌──────────────────┐
                    │ Signaux          │
                    │ explicables      │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ API FastAPI      │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Interface Web    │
                    └──────────────────┘

---

35. Feuille de route

Phase 1 — Fondations

- structure du dépôt ;
- environnement Python ;
- configuration ;
- PostgreSQL ;
- modèles de données ;
- premiers tests.

Phase 2 — Données

- identification des sources ;
- collecte ;
- validation ;
- nettoyage ;
- import historique ;
- historisation.

Phase 3 — Analyse

- indicateurs techniques ;
- indicateurs fondamentaux ;
- valorisation ;
- volatilité ;
- liquidité ;
- analyse sectorielle.

Phase 4 — Rétro-tests

- moteur de simulation ;
- stratégies ;
- coûts ;
- métriques ;
- rapports.

Phase 5 — Machine Learning

- création des jeux de données ;
- entraînement ;
- validation ;
- prédictions ;
- évaluation ;
- registre des modèles.

Phase 6 — Signaux

- notation ;
- règles ;
- explications ;
- historique des signaux.

Phase 7 — API

- FastAPI ;
- authentification ;
- endpoints ;
- intégration PostgreSQL.

Phase 8 — Interface

- tableau de bord ;
- cours ;
- graphiques ;
- entreprises ;
- analyses ;
- signaux ;
- performances.

Phase 9 — Automatisation

- pipeline quotidien ;
- pipeline hebdomadaire ;
- surveillance ;
- rapports ;
- amélioration continue.

---

36. Principes de fiabilité

BRVM-AI doit respecter plusieurs principes.

Ne jamais inventer une donnée

Une donnée absente doit être indiquée comme absente.

Ne jamais masquer une donnée incertaine

Les résultats doivent pouvoir être accompagnés d'un niveau de confiance ou d'une indication de qualité lorsque pertinent.

Ne jamais confondre corrélation et causalité

Une relation statistique ne démontre pas nécessairement une relation causale.

Ne jamais présenter un backtest comme une performance future

Une performance historique ne garantit pas une performance future.

Éviter le data leakage

Les informations futures ne doivent pas contaminer les données historiques utilisées pour entraîner ou tester un modèle.

Conserver la traçabilité

Chaque résultat important doit pouvoir être relié aux données et à la méthodologie ayant permis de l'obtenir.

---

37. Limites

BRVM-AI dépend notamment :

- de la disponibilité des données ;
- de leur qualité ;
- de leur fréquence ;
- de leur historique ;
- des sources utilisées ;
- de la liquidité du marché ;
- des hypothèses des modèles ;
- des conditions de marché.

Aucun modèle statistique ou d'intelligence artificielle ne permet de garantir une performance financière future.

---

38. Utilisation responsable

BRVM-AI est avant tout un outil d'analyse et de recherche quantitative.

Les résultats doivent être interprétés en tenant compte :

- des données disponibles ;
- de la méthodologie ;
- des hypothèses ;
- des limites statistiques ;
- des risques de marché ;
- des coûts de transaction ;
- de la liquidité ;
- des changements de régime de marché.

Les décisions financières finales restent sous la responsabilité de l'utilisateur.

---

39. Licence

La licence du projet sera définie selon les conditions retenues par le propriétaire du dépôt.

---

40. Statut du projet

Statut : développement initial

Les éléments présents dans la structure du dépôt constituent l'architecture initiale du projet.

Les modules seront implémentés progressivement.

[ ] Collecte
[ ] Base de données
[ ] Nettoyage
[ ] Indicateurs
[ ] Analyses
[ ] Rétro-tests
[ ] Modèles IA
[ ] Signaux
[ ] API
[ ] Interface
[ ] Automatisation
[ ] Monitoring

---

41. Nom du projet

BRVM-AI

Projet personnel d'analyse financière et quantitative orienté BRVM/UEMOA.

---

BRVM-AI

«Collecter. Comprendre. Tester. Modéliser. Analyser.»


## Socle Python livré

Le dépôt dispose maintenant d’un socle installable et vérifié pour la configuration, la qualité des données, les statistiques, les ratios fondamentaux et un backtest long-only sans look-ahead. Il ne contient pas de données BRVM réelles ni de collecteur actif.

- Installation et variables d’environnement : [Guide du socle Python](documentation/socle_python.md)
- Installer les dépendances de développement : `python -m pip install -e ".[dev]"`
- Contrôler le code : `ruff check .`, `ruff format --check .`, `mypy src`, `pytest`
- La CI GitHub Actions valide les changements Python; les workflows quotidien et hebdomadaire restent inactifs faute de source autorisée et de tâches de collecte réellement implémentées.
