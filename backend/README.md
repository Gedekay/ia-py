# SAAJD Backend

Backend REST FastAPI du Système d'Analyse Assistée de Dossiers Judiciaires.
Le service aide à vérifier la complétude et la régularité procédurale ; il ne
détermine jamais de culpabilité et ne remplace pas une décision judiciaire.

## Démarrage local

Depuis `backend/`, copier `.env.example` vers `.env`, remplacer les secrets,
puis lancer `docker compose up --build`. L'API est disponible sur
`http://localhost:8000` et son état sur `/health`.

Pour un développement Python local, installer `requirements.txt`, démarrer les
services PostgreSQL, Redis et MinIO, puis lancer `uvicorn app.main:app --reload`.
En développement, l'API crée les tables et le bucket MinIO au démarrage. En
production, appliquer les migrations Alembic avant de lancer les instances.
Créer le premier administrateur avec `SAAJD_ADMIN_PASSWORD='...' python -m app.cli
--email admin@example.org --full-name 'Administrateur SAAJD'`. Saisir le mot de
passe dans l'environnement du terminal, jamais dans le dépôt.

## Tests

Depuis `backend/`, exécuter `pytest`.

## Source constitutionnelle

`app/data/constitution_rdc.json` doit contenir le texte officiel vérifié selon
le format défini dans le document technique. Le dépôt ne contient pas cette
source. Le registre est donc volontairement vide ; toute analyse qui nécessite
une référence constitutionnelle non vérifiable doit échouer, jamais fabriquer
une citation.