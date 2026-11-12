# Déploiement — écarts et blocages constatés

Annexe de [deployment.md](deployment.md). Chaque ligne est constatée par lecture du code au
SHA `6e827ff`, pas déduite d'une intention documentaire. Aucune n'est corrigée par D01 :
`docker-compose.yml`, `Dockerfile`, `.env.example` et `app/` sont hors de son ownership.
Verdict de livraison : [qa/release.md](qa/release.md).

| ID | Écart | Preuve dans le dépôt | Effet sur un déploiement |
|---|---|---|---|
| GAP-01 | NPM conteneurisé ne peut pas joindre une publication `127.0.0.1` | `docker-compose.yml` : `ports: ["127.0.0.1:${API_PORT:-8000}:8000"]` | **bloquant** : il faut un NPM en `network_mode: host` ou un réseau externe partagé dans le Compose |
| GAP-02 | ~~Tous les quotas par IP se concentrent sur l'adresse du proxy~~ **corrigé** | `Dockerfile` ne passe plus `--no-proxy-headers` ; `FORWARDED_ALLOW_IPS` est requis dans `docker-compose.yml` ; non-régression : `tests/infra/test_proxy_headers.py` | **action opérateur** : fixer `FORWARDED_ALLOW_IPS` à l'adresse du proxy sur le réseau partagé, jamais un joker. Non renseigné, uvicorn ignore les en-têtes transmises et le défaut d'origine revient, sans faille d'usurpation |
| GAP-03 | Aucun middleware CORS ni préflight `OPTIONS` | `app/main.py` n'installe que `RequestContext` ; `CORS_*` d'`app/core/origins.py` inutilisés | bloquant **si et seulement si** le frontend n'est pas servi sur l'origine de l'API ; le déploiement même-origine A01-02 reste possible |
| GAP-04 | `APP_API_PUBLIC_ORIGIN`, `APP_SESSION_CROSS_SITE_ENABLED` et les réglages de pool ne sont pas transmis par le Compose | bloc `environment: &app-env` de `docker-compose.yml` | sessions cross-site non activables et pool non réglable sans modifier le Compose |
| GAP-05 | Readiness ne contrôle pas la révision Alembic | `app/main.py::ready` ne fait que `check_database` + `check_buckets` | un service « ready » peut tourner sur un schéma périmé ; `SCHEMA_NOT_READY` (X01) absent |
| GAP-06 | Ni rotation de journaux ni limite CPU/RAM pour les services de production | `docker-compose.yml` sans `logging:` ni `mem_limit`/`cpus` (présents seulement dans `ops/test-portainer/compose.yaml`) | disque saturable par les journaux, aucun plafond cgroup |
| GAP-07 | `APP_WORKERS` ne pilote pas uvicorn | `Dockerfile` CMD `--workers 2` figé ; `settings.workers` n'est lu que par la validation de budget | changer `APP_WORKERS` modifie la validation sans changer le runtime |
| GAP-08 | L'API utilise les credentials racine MinIO | `MINIO_ROOT_USER/PASSWORD` recopiés en `APP_STORAGE_ACCESS_KEY/SECRET_KEY` | privilèges de stockage excessifs ; pas de compte de service restreint |
| GAP-09 | Module portfolio absent : pas de schéma `0003`, pas de commande de nettoyage | `migrations/versions/` s'arrête à `0002_profiles` ; `app/modules/portfolio/` inexistant | la planification horaire définie dans [deployment-ops.md](deployment-ops.md) n'est pas activable ; uploads et publication indisponibles |
| GAP-10 | Entretien des quotas et des vues non planifié | `purge_expired` sans appelant planifié ; aucune commande pour `profile_view_dedup` | `rate_limit_windows` et `profile_view_dedup` croissent sans borne |
| GAP-11 | L'image runtime ne contient ni `alembic.ini` ni `migrations/` | `Dockerfile` ne copie que `pyproject.toml`, `uv.lock`, `app` | les migrations exigent un checkout hôte et un conteneur jetable avec montages |
| GAP-12 | Sauvegarde et restauration inexistantes | ni `ops/backup/` ni `docs/backup.md` (mission B01 non livrée) | **bloquant** : aucun retour arrière de données, aucun RPO/RTO mesuré |
| GAP-13 | Routes métier non assemblées | `app/main.py` n'expose que `/health/live` et `/health/ready` ; aucun routeur monté (X01 non livrée) | déployer aujourd'hui ne sert aucune fonctionnalité produit |
| GAP-14 | Modules recherche et portfolio absents | `app/modules/discovery/` et `app/modules/portfolio/` inexistants (R01, O01 non livrées) | périmètre MVP incomplet |

## Capacités délibérément absentes (pas des défauts)

- **Envoi d'email et réinitialisation de mot de passe** : `DisabledEmail.send_password_reset`
  (`app/shared/ports.py`) lève `EmailUnavailable` → 503 `EMAIL_UNAVAILABLE`. C'est la décision
  du plan : adaptateur désactivé avec erreur explicite, aucun faux succès, aucun fournisseur à
  intégrer au MVP. Aucune variable d'environnement SMTP n'existe et aucune ne doit être créée.
  L'exploitant doit donc traiter les demandes de réinitialisation hors application.
- **Adaptateur de stockage réel** : `DisabledStorage` (`app/shared/storage_disabled.py`) lève
  `StorageUnavailable` pour toutes les opérations. `APP_STORAGE_PUBLIC_ENDPOINT` est validé au
  démarrage mais encore inutilisé par du code applicatif ; seul `app/main.py` parle à MinIO,
  pour le bootstrap des buckets et la sonde de readiness.
- OAuth, comptes recruteurs, messagerie interne, modération, bucket public, URL GET signée et
  cache CDN sont hors MVP par décision et ne doivent pas être configurés.

## Mesures jamais effectuées — à ne pas présenter comme acquises

- Aucun test de charge (Q02) : pas de p95, pas de débit, pas d'empreinte CPU/RAM. La cible
  « 500 comptes, 100 utilisateurs simultanés » reste à démontrer.
- Aucune répétition de sauvegarde/restauration (B01) : RPO et RTO inconnus.
- Aucun `docker compose build`, `up`, `exec`, `alembic upgrade` ni appel Portainer exécuté par
  D01 : l'environnement de cette mission n'a ni démon Docker ni base de données, et la mission
  est documentaire (« aucun déploiement exécuté »).
- Aucune preuve QA indépendante enregistrée pour F02, M01, M02, I01 et P01 : `docs/qa/` ne
  contient que `A01.md`, `F01.md`, `F01-REMOTE.md` et `test-strategy.md`.
