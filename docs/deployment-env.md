# Déploiement — référence des variables d'environnement

Annexe de [deployment.md](deployment.md). Dérivée intégralement de
`app/core/config.py`, `app/core/config_urls.py`, `app/core/origins.py` et
`docker-compose.yml` au SHA `6e827ff`. Aucune variable inventée.

Préfixe obligatoire `APP_` et `extra="forbid"` : **toute variable `APP_*` inconnue fait
échouer le démarrage**. `hide_input_in_errors=True` : les erreurs de validation ne
réaffichent pas les valeurs. Les secrets sont des `SecretStr` et ne sortent ni dans
`/health`, ni dans les erreurs, ni dans les journaux.

## Variables applicatives `APP_*`

| Variable | Secret | Défaut | Contrainte appliquée au démarrage | Exemple |
|---|---|---|---|---|
| `APP_ENVIRONMENT` | non | **requis** | exactement `local`, `test` ou `production` | `production` |
| `APP_DATABASE_URL` | **oui** | **requis** | `postgresql+psycopg://` ; hôte, base, utilisateur et mot de passe tous présents ; aucune chaîne de requête ; port 1..65535 si fourni | `postgresql+psycopg://app:<MOT_DE_PASSE>@db/app` |
| `APP_STORAGE_ENDPOINT` | non | **requis** | origine interne ; `http` autorisé (`internal=True`) ; ni identifiants, ni chemin, ni requête, ni fragment ; slash final retiré | `http://minio:9000` |
| `APP_STORAGE_PUBLIC_ENDPOINT` | non | **requis** | **HTTPS obligatoire** sauf `local`/`test` où `http://` sur boucle locale est toléré | `https://files.diddifree.com` |
| `APP_STORAGE_ACCESS_KEY` | **oui** | **requis** | longueur ≥ 1 | `<ACCESS_KEY>` |
| `APP_STORAGE_SECRET_KEY` | **oui** | **requis** | longueur ≥ 1 | `<SECRET_KEY>` |
| `APP_QUARANTINE_BUCKET` | non | **requis** | `^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$` (3..63) ; différent du bucket validé | `quarantine` |
| `APP_VALIDATED_BUCKET` | non | **requis** | même motif ; différent du bucket de quarantaine | `validated` |
| `APP_FRONTEND_ORIGIN` | non | **requis** | allowlist `is_allowed_origin` (voir [deployment-network.md](deployment-network.md)) ; valeur normalisée | `https://diddifree.com` |
| `APP_QUOTA_HMAC_SECRET` | **oui** | **requis** | longueur ≥ 32 caractères | `<32+ CARACTÈRES ALÉATOIRES>` |
| `APP_SECURE_COOKIES` | non | `true` | littéralement `true` ou `false` (casse libre), rien d'autre ; doit être `true` hors `local`/`test` | `true` |
| `APP_SESSION_CROSS_SITE_ENABLED` | non | `false` | même parsing strict ; si `true`, exige cookies Secure **et** `APP_API_PUBLIC_ORIGIN` en `https://` | `false` |
| `APP_API_PUBLIC_ORIGIN` | non | absent | origine `http`/`https` normalisée, sans chemin ni userinfo ; **non soumise à l'allowlist frontend** ; requise si cookies non Secure (alors `http://localhost[:port]` seulement) ou si cross-site actif | `https://diddifree.com` |
| `APP_WORKERS` | non | `2` | entier 1..20 ; n'entre que dans le budget de connexions, **ne pilote pas uvicorn** (GAP-07) | `2` |
| `APP_POOL_SIZE` | non | `5` | entier 1..20 ; passé à `create_engine` | `5` |
| `APP_MAX_OVERFLOW` | non | `5` | entier 0..20 ; passé à `create_engine` | `5` |
| `APP_POOL_TIMEOUT` | non | `3` | entier **1..3** secondes (borne haute stricte) | `3` |
| `APP_STATEMENT_TIMEOUT_MS` | non | `3000` | entier **1..3000** ms ; injecté en `-c statement_timeout=` | `3000` |

Validations croisées supplémentaires, toutes bloquantes au démarrage :

- `APP_WORKERS × (APP_POOL_SIZE + APP_MAX_OVERFLOW) ≤ 20` — « API connection budget exceeds 20 ».
- Buckets de quarantaine et validé obligatoirement distincts — « Separate private buckets required ».
- Cookies non Secure uniquement avec une API HTTP locale — « Insecure cookies require a local HTTP API ».
- Hors `local`/`test`, cookies Secure imposés — « Secure cookies required outside local/test ».

## Variables lues par Compose (hôte, pas par l'application)

| Variable | Défaut | Rôle |
|---|---|---|
| `COMPOSE_PROJECT_NAME` | nom du répertoire | isole projet, réseau et volumes |
| `POSTGRES_PASSWORD` | **requis** (`:?`) | mot de passe du rôle `app` ; recopié dans `APP_DATABASE_URL` par le Compose, donc **doit être sûr pour une URL** (pas de `@ : / ? # %`) |
| `POSTGRES_DB` | `app` | nom de la base |
| `MINIO_ROOT_USER` | **requis** | identifiant racine MinIO, réutilisé comme `APP_STORAGE_ACCESS_KEY` |
| `MINIO_ROOT_PASSWORD` | **requis** | secret racine MinIO, réutilisé comme `APP_STORAGE_SECRET_KEY` |
| `API_PORT` | `8000` | port loopback publié pour l'API |
| `STORAGE_PORT` | `9000` | port loopback publié pour MinIO S3 |

Le Compose fixe lui-même `APP_STORAGE_ENDPOINT=http://minio:9000`,
`APP_QUARANTINE_BUCKET=quarantine` et `APP_VALIDATED_BUCKET=validated` ; il ne transmet
**pas** `APP_API_PUBLIC_ORIGIN`, `APP_SESSION_CROSS_SITE_ENABLED`, `APP_WORKERS`,
`APP_POOL_SIZE`, `APP_MAX_OVERFLOW`, `APP_POOL_TIMEOUT` ni `APP_STATEMENT_TIMEOUT_MS` :
leurs défauts s'appliquent et ne sont pas réglables sans modifier le Compose (GAP-04).

## Gestion des secrets

- Partir de `.env.example` (placeholders uniquement) vers un fichier **non versionné** :
  `.gitignore` ignore `.env` et `.env.*` sauf `.env.example`. Ne jamais committer de valeur réelle.
- Fichier d'environnement hors contexte de build, propriétaire root, permissions `600`,
  et **jamais** dans le répertoire envoyé au builder.
- Générer chaque secret indépendamment, par exemple `openssl rand -base64 48` pour
  `APP_QUOTA_HMAC_SECRET`, et un mot de passe Postgres alphanumérique pour rester URL-safe.
- `APP_QUOTA_HMAC_SECRET` est la clé de hachage des quotas : sa rotation invalide toutes les
  fenêtres en cours et remet les compteurs à zéro ; la planifier en période calme.
- `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD` servent aujourd'hui de credentials applicatifs :
  l'API dispose donc des privilèges racine du stockage. Un compte de service restreint est
  souhaitable mais exigerait une modification du Compose (GAP-08).
- Rotation d'un secret : mettre à jour le fichier d'environnement puis recréer le service
  concerné ; un démarrage avec une valeur invalide est refusé immédiatement, pas dégradé.
