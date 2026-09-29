# Guide du socle Python BRVM-AI

## Portée réelle

Ce dépôt contient un **socle Python extensible**, pas encore la plateforme BRVM-AI complète. Il fournit une configuration typée, des exceptions et une journalisation, des contrôles OHLCV, des statistiques descriptives, des indicateurs simples, des ratios fondamentaux et un moteur de backtest pédagogique long-only. Les intégrations futures (source de marché, base de données, API web, modèle IA, notifications, interface et agent Telegram) ne sont pas présentées comme déjà opérationnelles.

Aucun cours ni fondamental BRVM réel n’est livré. Les valeurs numériques des tests sont de petites fixtures synthétiques, exclusivement destinées à vérifier les formules.

## Prérequis et installation

Le projet cible Python `>=3.12,<3.14`.

```bash
python --version
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows PowerShell : .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Installation des seules dépendances d’exécution :

```bash
python -m pip install -e .
```

Extras optionnels déclarés dans `pyproject.toml` :

| Extra | Contenu | À installer lorsque… |
|---|---|---|
| `dev` | pytest, pytest-cov, Ruff, mypy, pandas-stubs | développement et CI |
| `statistics` | Polars, SciPy, statsmodels | une tâche statistique les utilise effectivement |
| `machine-learning` | scikit-learn | un modèle supervisé/non supervisé est implémenté |
| `boosting` | XGBoost, LightGBM | une expérience de boosting les nécessite |
| `database` | SQLAlchemy, psycopg, Alembic | le dépôt persistant et ses migrations sont implémentés |
| `api` | FastAPI, HTTPX, Uvicorn | des routes ou clients HTTP deviennent nécessaires |

Exemple d’installation ciblée : `python -m pip install -e ".[dev,database]"`. Les extras optionnels ne sont pas installés avec `.[dev]`.

## Configuration et secrets

Copier `.env.exemple` en `.env` localement, puis ne renseigner que les variables requises par une intégration activée. `.env` est ignoré par Git. Le fichier d’exemple ne contient aucune clé réelle. En CI, les variables peuvent être fournies par l’environnement ou les secrets GitHub : le dépôt ne dépend pas d’un fichier secret.

Les valeurs sensibles sont représentées avec `SecretStr` et ne doivent pas être journalisées. Les intégrations sont désactivées par défaut. Une clé n’est obligatoire que si la fonctionnalité correspondante est activée.

| Variables | Requis / défaut | Condition et validation |
|---|---|---|
| `ENVIRONNEMENT` | Facultatif, `developpement` | Valeurs admises : `developpement`, `test`, `production` |
| `VERSION_APPLICATION` | Facultatif, `0.1.0` | Chaîne nettoyée des espaces |
| `NIVEAU_JOURNALISATION` | Facultatif, `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` ou `CRITICAL` |
| `ACTIVER_BASE_DE_DONNEES` | Facultatif, `false` | Si vrai, `BASE_DE_DONNEES_URL` est requise; URL PostgreSQL seulement |
| `BASE_DE_DONNEES_URL` | Facultatif | Secret; schémas `postgresql` ou `postgresql+psycopg`, hôte obligatoire |
| `ACTIVER_API_INTERNE` | Facultatif, `false` | Si vrai, `URL_API` et `CLE_API_INTERNE` sont requises |
| `URL_API` | Facultatif | URL HTTP(S) validée par Pydantic |
| `CLE_API_INTERNE` | Facultatif | Clé secrète; requise avec `ACTIVER_API_INTERNE=true` |
| `ACTIVER_API_DONNEES_MARCHE` | Facultatif, `false` | Si vrai, `CLE_API_DONNEES_MARCHE` est requise |
| `CLE_API_DONNEES_MARCHE` | Facultatif | Secret d’un fournisseur choisi par l’utilisateur; aucun fournisseur/API n’est inventé |
| `ACTIVER_EMAIL` | Facultatif, `false` | Si vrai, `EMAIL_HOTE` et `EMAIL_EXPEDITEUR` sont requis |
| `EMAIL_HOTE` | Facultatif | Obligatoire si l’email est activé |
| `EMAIL_PORT` | Facultatif, `587` | Entier entre 1 et 65535 |
| `EMAIL_UTILISATEUR`, `EMAIL_MOT_DE_PASSE` | Facultatifs | Authentification SMTP optionnelle; si l’un est renseigné, les deux le sont |
| `EMAIL_EXPEDITEUR` | Facultatif | Obligatoire si l’email est activé; validation de forme d’adresse |
| `ACTIVER_TELEGRAM` | Facultatif, `false` | Si vrai, token et identifiant de chat requis |
| `TELEGRAM_BOT_TOKEN` | Facultatif | Secret; requis avec Telegram activé |
| `TELEGRAM_CHAT_ID` | Facultatif | Requis avec Telegram activé |
| `ACTIVER_IA` | Facultatif, `false` | Si vrai, fournisseur, clé et modèle requis |
| `FOURNISSEUR_IA`, `MODELE_IA` | Facultatifs | Noms fournis par l’utilisateur, aucune API simulée |
| `CLE_API_IA` | Facultatif | Secret; requis avec l’IA activée |
| `ACTIVER_API` | Facultatif, `false` | Si vrai, `CLE_SECRETE` est requise |
| `CLE_SECRETE` | Facultatif | Secret de 32 caractères minimum; obligatoire seulement si l’API est activée |
| `FREQUENCE_COLLECTE_MINUTES` | Facultatif, `1440` | Entier entre 1 et 10080; paramètre futur, aucun ordonnanceur ne l’utilise à ce stade |
| `FUSEAU_HORAIRE` | Facultatif, `Africa/Abidjan` | Identifiant IANA validé |
| `NOMBRE_MAX_TENTATIVES` | Facultatif, `3` | Entier entre 0 et 10; paramètre futur, aucune reprise automatique n’est encore exécutée |

Utilisation explicite dans le code :

```python
from brvm_ia.configuration import charger_parametres

parametres = charger_parametres()
```

`obtenir_parametres()` fournit une instance mise en cache pour le processus courant. Les erreurs de validation sont converties en diagnostic `ErreurConfiguration` sans inclure les valeurs secrètes.

## API d’analyse livrée

### Qualité des cotations

`brvm_ia.nettoyage.validation.valider_donnees_marche` vérifie les colonnes `date`, `entreprise`, `ticker`, `ouverture`, `plus_haut`, `plus_bas`, `cloture`, `volume`; les valeurs absentes/non numériques/non finies, les dates invalides ou futures, les tickers vides, les prix non positifs, les volumes négatifs, l’ordre OHLC et les doublons temporels. Le rapport localise les anomalies par position de ligne et colonne sans recopier les valeurs. `exiger_donnees_marche_valides` convertit les erreurs bloquantes en `ErreurValidationDonnees`.

Les mouvements extrêmes ne sont pas universellement définis : un `seuil_alerte_variation_absolue` explicite peut produire un avertissement non bloquant; aucun seuil de marché n’est inventé. Pour le contrôle de fréquence, l’appelant peut fournir `dates_attendues` provenant d’un calendrier autorisé. Une date observée absente de ce calendrier est signalée comme erreur; une séance attendue sans observation par ticker est un avertissement. Sans calendrier fourni, le code ne prétend pas connaître les jours de cotation BRVM.

Exemple avec un DataFrame chargé par l’application à partir d’une source autorisée :

```python
from brvm_ia.nettoyage import valider_donnees_marche

rapport = valider_donnees_marche(cotations)
if not rapport.est_valide:
    for anomalie in rapport.erreurs:
        print(anomalie.code, anomalie.position_ligne, anomalie.colonne)
```

Cet exemple suppose que `cotations` a déjà été obtenu par l’application; aucune fonction de collecte réelle n’est livrée.

### Statistiques et indicateurs

- `decrire_serie` calcule moyenne, médiane, minimum, maximum, variance et écart-type d’échantillon (`ddof=1`), quantiles 25/75 et taille; au moins deux observations sont requises par défaut.
- `statistiques_glissantes` fournit moyenne et écart-type glissants, sans imputation des données absentes.
- `rendements_simples`, `rendements_logarithmiques`, `rendement_cumule`, `volatilite_annualisee` et `drawdown_maximal` opèrent sur les cours ou rendements effectivement fournis. Les cours de clôture doivent être positifs, les observations valides, et tout index `DatetimeIndex` doit être unique et chronologique.
- La volatilité annualisée utilise 252 périodes par an par défaut; ce paramètre peut être remplacé par l’appelant selon la fréquence réelle. Un minimum de 20 observations est imposé par défaut; la fonction lève `ErreurAnalyse` au lieu d’afficher une volatilité présentée comme fiable sur un historique trop court.

### Fondamentaux

`DonneesFondamentales` et `calculer_ratios_fondamentaux` traitent chiffre d’affaires, résultat net, capitaux propres, actifs, passifs, dividende par action, bénéfice par action et cours. Les champs inconnus restent `None`; un dénominateur nul ou indisponible ne produit pas un ratio inventé. Le PER n’est calculé que si le bénéfice par action est positif. Les résultats supposent que les données fournies sont comparables (même période, devise et méthode comptable), ce que le socle ne vérifie pas encore.

### Rétro-tests livrés et limites

`simuler_strategie_longue` accepte des cours de clôture datés et des signaux binaires `0` (hors marché) / `1` (long). Un signal connu à la clôture `t` n’est appliqué qu’à partir de `t+1`. Les frais configurés en points de base sont déduits à l’entrée et à la sortie. `calculer_metriques_backtest` calcule rendement total, drawdown maximal, nombre de changements de position et volatilité si l’échantillon atteint le minimum configuré.

Ce moteur est un **backtest prix-only minimal**, pas un simulateur d’exécution complet : pas de dividendes, slippage, fiscalité, liquidité, contraintes d’ordres ni positions courtes. Il ne corrige pas le survivorship bias; les historiques d’univers/tickers actifs à chaque date ne sont pas encore disponibles. Les signaux doivent être calculés sans données futures par l’appelant.

## Qualité, tests et intégration continue

Commandes locales exécutées aussi par GitHub Actions :

```bash
ruff check .
ruff format --check .
mypy src
pytest --cov=brvm_ia --cov-report=term-missing
```

Le workflow `.github/workflows/tests.yml` s’exécute sur les pushes vers `main`, les pull requests vers `main` et à la demande, sous Python 3.12 et 3.13. Il installe `.[dev]`, n’exige aucun secret et n’accorde que la permission de lecture du dépôt.

Les fichiers `pipeline_quotidien.yml` et `pipeline_hebdomadaire.yml` sont conservés mais ne déclenchent rien : il n’existe pas encore de connecteur/source BRVM réel, de collecteur fonctionnel, ni de décision utilisateur sur le calendrier de production. Les activer maintenant créerait une automatisation fictive. `FREQUENCE_COLLECTE_MINUTES` et `NOMBRE_MAX_TENTATIVES` ne sont, pour l’instant, que des paramètres de configuration.

## Fonctionnalités non livrées dans cette étape

- ingestion de cotations ou données fondamentales réelles, fournisseur/API et règles d’autorisation;
- persistance PostgreSQL, ORM, schéma et migrations;
- serveur FastAPI, interface Next.js, routes et authentification;
- modèles de machine learning, entraînement/évaluation et registre;
- signaux d’investissement et explications;
- ordonnanceur quotidien/hebdomadaire, reprises automatiques et notifications SMTP/Telegram;
- agent conversationnel, interface web et analyse interentreprises complète;
- calendrier de trading BRVM officiel et correction du survivorship bias.

Ces limites sont intentionnelles afin que le dépôt ne présente pas des placeholders ou des données fictives comme des fonctionnalités disponibles.
