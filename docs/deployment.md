# Déploiement — runbook opérateur (D01)

État : **document d'exploitation ; aucun déploiement exécuté par cette mission.**
Il décrit le code présent au SHA de base `6e827ff`, pas un déploiement générique.
Les capacités manquantes sont listées dans [deployment-gaps.md](deployment-gaps.md) ;
le gate de livraison dans [qa/release.md](qa/release.md).

Compléments : [variables d'environnement](deployment-env.md) ·
[TLS, proxy, CORS et sessions](deployment-network.md) ·
[migrations, nettoyage, déploiement, montée de version, retour arrière](deployment-ops.md).

## Prérequis

- Hôte Linux x86-64, Docker Engine et plugin Compose v2.
- Nginx Proxy Manager (NPM) déjà en service, terminaison TLS et certificat valide
  pour le nom public du frontend ; DNS public résolu vers l'hôte.
- Checkout git du dépôt au SHA livré **sur l'hôte** : `docker-compose.yml` utilise
  `build: {context: ., target: runtime}` et aucune image n'est publiée en registre.
  Le checkout est aussi requis pour Alembic (voir deployment-ops.md).
- Accès réseau sortant au build : `ghcr.io/astral-sh/uv:0.11.6`, `python:3.13-slim-bookworm`,
  PyPI. `uv sync --locked --no-dev --no-install-project --no-build` échoue au lieu de
  compiler une source native : des wheels binaires sont obligatoires.
- Espace disque pour deux volumes nommés. Aucun dimensionnement mesuré (voir Q02).
- L'application **ne lit aucun fichier `.env`** : `Settings` (`app/core/config.py`) n'a pas
  d'`env_file`. Les variables viennent de l'environnement du processus ; `--env-file` de
  Compose ne sert qu'à l'interpolation du fichier Compose.

## Réseau et ports

| Service | Image / build | Publication | Règle |
|---|---|---|---|
| `api` | build local, stage `runtime` | `127.0.0.1:${API_PORT:-8000}` → 8000 | jamais exposé hors loopback |
| `db` | `postgres:16-alpine` | **aucune** | 5432 reste strictement privé |
| `minio` | `quay.io/minio/minio:RELEASE.2025-04-22T22-12-26Z` | `127.0.0.1:${STORAGE_PORT:-9000}` → 9000 | S3 privé ; console `:9001` écoute dans le conteneur et **n'est pas publiée** |
| `buckets` | build local, stage `runtime` | aucune | bootstrap unique, `restart: "no"` |
| `tests`, `core-tests` | stage `test` | aucune | profil `test` / `extends` : jamais démarrés en production |

Buckets privés : `initialize_buckets()` crée les deux buckets manquants puis appelle
`delete_bucket_policy`. `check_buckets()` **échoue fermé** : si une policy existe sur
l'un des buckets, `/health/ready` renvoie 503. Ne jamais installer de policy anonyme,
ne jamais publier 9001, ne jamais ajouter de port au service `db`.

Accessibilité depuis NPM : la publication est liée à `127.0.0.1`. Un NPM conteneurisé sur
son propre réseau bridge **ne peut pas** joindre `127.0.0.1:8000` de l'hôte. Il faut soit un
NPM en `network_mode: host`, soit rattacher `docker-compose.yml` à un réseau externe
partagé — modification hors ownership D01, voir GAP-01.

## Volumes persistants

`postgres-data` → `/var/lib/postgresql/data`, `minio-data` → `/data` : volumes nommés,
portés par le projet Compose, services en `restart: unless-stopped`. **Ne jamais exécuter
`docker compose down -v`** ni supprimer ces volumes. Les conteneurs `api` et `buckets` sont
`read_only` avec `tmpfs: [/tmp]`, `cap_drop: [ALL]`, `no-new-privileges` et UID 10001 :
aucun fichier envoyé par un utilisateur n'atterrit sur le système de fichiers du conteneur.

## Santé

- `GET /health/live` → 200 `{"status":"ok"}` dès que le processus répond ; aucune dépendance.
- `GET /health/ready` → 200 `{"status":"ready"}` si `SELECT 1` réussit **et** que les deux
  buckets existent sans policy ; sinon 503 `DEPENDENCY_UNAVAILABLE`.
  Il **ne vérifie pas la révision Alembic** : un readiness vert ne prouve pas que le schéma
  est à jour (`SCHEMA_NOT_READY` appartient à X01 et n'existe pas) — GAP-05.
- Healthcheck Compose : `urllib` sur `http://127.0.0.1:8000/health/ready`, `interval 30s`,
  `timeout 25s`, `retries 3`, `start_period 30s`. Sonder `/health/live` depuis NPM.
- Health est exempt de quota DB par contrat ; le laisser non authentifié mais joignable
  seulement depuis le proxy et l'hôte.

## Journaux et ressources

- Journaux applicatifs : une ligne JSON par réponse sur le logger `app.requests`
  (`request_id`, `route`, `status`, `duration_ms`) ; access log uvicorn désactivé ; les erreurs
  sortent enveloppées, sans corps, cookie, jeton CSRF ni secret.
- `docker-compose.yml` ne fixe **ni option de rotation de journaux ni limite CPU/mémoire** pour
  les services de production. Configurer la rotation au niveau du démon avant le premier
  déploiement et accepter l'absence de plafond cgroup — GAP-06.
- Budget connexions validé au démarrage : `workers × (pool_size + max_overflow) ≤ 20`, contre
  `max_connections=40` sur Postgres (marge pour migrations et `psql`). `statement_timeout`
  3000 ms, `connect_timeout` 3 s, `pool_timeout` 3 s.
- Capacité : 500 comptes et 100 utilisateurs simultanés sont un **objectif à démontrer** par
  Q02. Aucun test de charge n'a été exécuté : aucun p95, débit, CPU ou RAM n'est avancé ici.
