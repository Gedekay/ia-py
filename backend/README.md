# SAAJD Backend

API REST FastAPI du Système d'Analyse Assistée de Dossiers Judiciaires. Elle aide à repérer des pièces manquantes et des points de procédure à vérifier. Elle ne détermine jamais la culpabilité et ne remplace ni un avocat, ni un magistrat, ni une décision de justice.

Le dépôt contient le backend et son API ; il ne contient pas d'interface web.

## Prérequis

- Docker Engine et Docker Compose v2 en fonctionnement.
- Un terminal ouvert dans le dossier `backend/`.

Vérifier Docker avant de continuer :

```bash
docker compose version
docker info
```

## Démarrage avec Docker

Depuis la racine du dépôt :

```bash
cd backend
cp .env.example .env
```

Éditer `.env` et remplacer les valeurs de développement pour le secret JWT et le secret MinIO. Pour Docker Compose, les services se joignent par leur nom de service : utiliser ces URL dans `.env` :

```dotenv
DATABASE_URL=postgresql+asyncpg://saajd:saajd@postgres:5432/saajd
REDIS_URL=redis://redis:6379/0
MINIO_ENDPOINT=minio:9000
```

Lancer l'API, le worker Celery, PostgreSQL avec pgvector, Redis et MinIO :

```bash
docker compose up --build -d
```

Suivre le démarrage :

```bash
docker compose ps
docker compose logs -f api worker
```

En environnement `development`, l'API crée les tables et charge les articles du fichier `app/data/constitution_rdc.json` au démarrage. Attendre que le conteneur `api` soit démarré avant de continuer.

Adresses locales :

- API : <http://localhost:8000>
- OpenAPI/Swagger : <http://localhost:8000/docs>
- Santé des services : <http://localhost:8000/health>
- Console MinIO : <http://localhost:9001>

La santé doit renvoyer `"status":"ok"` lorsque PostgreSQL, Redis et MinIO répondent. `degraded` signale une dépendance indisponible.

Arrêter les services sans supprimer les données :

```bash
docker compose down
```

Pour supprimer également les volumes de données, commande destructive à utiliser uniquement si leur contenu peut être effacé :

```bash
docker compose down -v
```

## Créer le premier administrateur

Après le démarrage des services, saisir le mot de passe sans l’écrire dans le dépôt ni dans la commande :

```bash
printf 'Mot de passe administrateur (12 caractères minimum) : '
read -r -s SAAJD_ADMIN_PASSWORD
export SAAJD_ADMIN_PASSWORD
echo
docker compose exec -e SAAJD_ADMIN_PASSWORD api python -m app.cli \
  --email admin@example.org \
  --full-name 'Administrateur SAAJD'
unset SAAJD_ADMIN_PASSWORD
```

La commande refuse de créer un second compte avec la même adresse. L'administrateur peut ensuite créer les comptes enquêteur et magistrat avec l'API d'administration.

## Utiliser l'API

Les routes sont versionnées sous `/api/v1`. Les principaux parcours sont :

1. Se connecter avec `POST /api/v1/auth/login` pour recevoir les jetons d'accès et de renouvellement.
2. Créer un dossier avec `POST /api/v1/dossiers`.
3. Ajouter des pièces avec `POST /api/v1/dossiers/{dossier_id}/documents` en envoyant un fichier multipart/form-data. Formats acceptés : PDF, DOCX, TXT, JPEG, PNG et TIFF.
4. Attendre que l'extraction des pièces soit terminée, puis lancer `POST /api/v1/dossiers/{dossier_id}/analyses`.
5. Consulter l'état et le résultat avec `GET /api/v1/analyses/{analyse_id}`.
6. Exporter le résultat avec `GET /api/v1/analyses/{analyse_id}/report.json` ou `GET /api/v1/analyses/{analyse_id}/report.pdf`.

Pour les routes protégées, envoyer le jeton d'accès dans l'en-tête :

```http
Authorization: Bearer <access_token>
```

La liste complète des opérations, paramètres et schémas est visible dans `/docs` et `/openapi.json`. Les rôles limitent l'accès aux dossiers et aux opérations d'administration.

## Configurer l'analyse IA

Les vérifications procédurales et les garde-fous sont dans le backend. Pour activer l'analyse générative et la recherche d'articles, configurer dans `.env` un fournisseur compatible avec les routes `/chat/completions` et `/embeddings` :

```dotenv
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://adresse-du-fournisseur/v1
LLM_API_KEY=secret-fourni-par-votre-fournisseur
LLM_MODEL=nom-du-modele-chat
EMBEDDING_MODEL=nom-du-modele-embedding
```

Vérifier la compatibilité des modèles d'embedding avec les 1536 dimensions attendues par pgvector. Sans fournisseur configuré, les tâches d'analyse ne peuvent pas produire de résultat complet. Redémarrer les services après toute modification de `.env` :

```bash
docker compose up -d --force-recreate api worker
```

## Lancer en développement Python

Cette méthode démarre l'API sur l'hôte et nécessite toujours PostgreSQL, Redis et MinIO. Démarrer d'abord ces services, puis depuis `backend/` :

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Vérifier que les URL de `.env` pointent vers les ports locaux (`localhost`) pour ce mode, pas vers les noms de services Docker.

## Tests et migrations

Depuis `backend/` :

```bash
pytest -q
```

Pour générer le SQL de la migration sans se connecter à PostgreSQL :

```bash
alembic upgrade head --sql
```

En production, définir `ENV=production`, appliquer les migrations avec `alembic upgrade head`, créer le bucket MinIO et fournir les secrets via le gestionnaire de secrets du déploiement. La création automatique des tables au démarrage est réservée au développement.

## Données constitutionnelles et limites

Le registre `app/data/constitution_rdc.json` contient le texte constitutionnel structuré et sa source déclarée. Les références affichées par les analyses doivent correspondre exactement à un texte du registre. Le logiciel ne garantit pas à lui seul l'authenticité juridique de ce fichier : vérifier la source, la version applicable et les éventuelles révisions auprès d'une source officielle avant tout usage opérationnel.

L'extraction OCR nécessite Tesseract avec la langue française (`fra`), installée dans l'image Docker. Les documents téléchargés contiennent potentiellement des données judiciaires sensibles : limiter l'accès, protéger les secrets et les volumes, et appliquer les règles locales de conservation et de confidentialité.
