# Architecture A01 — contrat v1

État : prêt pour revue indépendante lorsque le suivi A01 est remis ; **non validé** avant QA. Ce document spécifie un système à construire, pas une implémentation existante.

## Autorité et provenance

Sources lues intégralement : [AGENTS.md](../AGENTS.md), [plan.md](../plan.md), [README.md](../README.md) et specs originales à `../../specs.md` depuis la racine du worktree A01 (hors dépôt backend). Base : `2d64a56bc9f8e6c48b8bf994bfbf6ab9b122b2d7`.

Le plan approuvé et la consigne de mission priment sur les specs. La mention « architecture validée » du README ne constitue pas une validation QA de ces nouveaux contrats. Aucun changement de ce README hors ownership.

Les specs originales sont une baseline documentaire, pas du code backend. Le retour Frontend est consultatif : les enums signalés sont retenus explicitement, mais aucune compatibilité parfaite avec une implémentation frontend n'est affirmée. Aucun frontend n'a été modifié ni testé dans A01.

Hérité : monolithe Python 3.12+, FastAPI, PostgreSQL, SQLAlchemy 2.x, Alembic, Pydantic 2.x, MinIO ; Docker Compose derrière Nginx Proxy Manager ; 500 comptes, 100 utilisateurs simultanés à démontrer ; comptes talents seulement ; profils/recherche/contacts anonymes ; visibilité des coordonnées choisie ; publication des fichiers après validation. Reset/email différés avec erreur explicite. OAuth, recruteurs, messagerie et modération hors MVP. Aucun frontend modifié.

Décisions nouvelles A01 : tous les nombres, champs, statuts, routes additionnelles, contraintes SQL et politiques ci-dessous et dans `contracts/` sont des décisions normatives proposées à QA. Ils ne sont pas des faits hérités. A01 fige v1 après QA et fusion ; toute évolution ultérieure passe par une mission de contrat et, si nécessaire, une migration dédiée.

## Décisions structurantes

| ID | Décision A01 et raison |
|---|---|
| A01-01 | API `/api/v1`, JSON strict, erreurs stables ; contrats [HTTP](contracts/http.md), [identité](contracts/identity.md), [profils/recherche](contracts/profiles.md), [portfolio](contracts/portfolio.md). |
| A01-02 | Frontend et API servis sous la même origine HTTPS ; `/api` routé vers API. Cookies host-only, CSRF avec jeton lié à session et contrôle Origin. Aucun besoin de cookies cross-site. |
| A01-03 | Sessions opaques révocables PostgreSQL ; aucun JWT ni Redis. Quotas partagés atomiques en PostgreSQL, jamais compteur mémoire seul. |
| A01-04 | Profils publics dès création valide ; contacts privés par défaut. Aucun brouillon de profil ni modération. Portfolio reste privé avant publication explicite. |
| A01-05 | Upload direct présigné vers bucket privé de quarantaine, puis validation et copie immuable privée ; livraison par API avec contrôle de publication à chaque requête. Pas de bucket public ni d'URL GET signée exposée. |
| A01-06 | Validation synchrone bornée et reprise explicite ; aucun service worker supplémentaire requis. Objets temporaires et orphelins nettoyés par commande O01 planifiée dans le conteneur API par exploitation D01. |
| A01-07 | Suppression de profil atomique en DB, invalidation immédiate des accès publics ; nettoyage physique MinIO retryable. Pas de suppression de compte au MVP. |
| A01-08 | `profile_views` conservé comme compteur quotidien agrégé sans IP persistante ; reset token réservé vide ; pas de fonctionnalité email simulée. |
| A01-09 | F02 possède temporairement `app/main.py` pour health uniquement, puis transfert exclusif à X01. Les modules livrent des routeurs testés par fabriques de tests locales sans modifier main. |
| A01-10 | Chaque source manuelle et test : **moins de 100 lignes** (99 au plus, consigne A01 plus stricte que plafond 100 du plan). Documentation libre. Exceptions générées/locks/migrations explicitement recensées, aucune exception active en A01. |

## Structure et dépendances

`app/core/` : configuration, engine/pool DB, primitives sécurité, logs, santé et quotas. `app/shared/` : ports, erreurs, DTO partagés, pagination et dépendances d'authentification injectables. Les modules ont `models/`, `schemas/`, `repository/`, `service/`, `routes/`, découpés en fichiers courts ; aucun nom de fichier monolithique imposé.

Identité dépend de core/shared ; profiles dépend du principal identité ; contact dépend de profiles ; portfolio dépend du principal et de l'existence du profil ; discovery lit des projections publiques de profiles/contact et des éléments portfolio publiés. Pas d'appel HTTP entre modules. Un module ne modifie pas les tables d'un autre : orchestration des suppressions par transaction/service et FK, pas d'import de routeurs entre services. X01 assemble les routeurs et handlers sans réécrire les services.

F01 livre les interfaces injectables : `Principal(user_id, session_id)`, horloge UTC, générateur de secrets, transaction DB, `StoragePort` (presign_post/head/read_stream/copy/delete), `EmailPort.send_password_reset(to, url)` ; adaptateur email désactivé lève `EmailUnavailable`, mappé 503. Aucune clé réelle ni URL reset dans les logs. Storage distingue absent, indisponible et invalide ; pas de succès silencieux. I01 fournit le résolveur de Principal ; son injection ne requiert pas de changement F01.

Le modèle SQL normatif et la séquence Alembic sont dans [data.md](contracts/data.md). F01 définit Base et conventions de nommage ; M01/M02/M03 écrivent le DDL Alembic sans importer de modèles futurs. Chaque module écrit ensuite ses modèles conformes au schéma déjà migré. Alembic charge les métadonnées disponibles, mais la migration initiale ne dépend pas d'I01. Chaque migration est vérifiée contre un état réel, pas seulement par autogenerate.

## Exploitation et sécurité

Configuration validée au démarrage : URL DB, endpoint MinIO interne, endpoint présigné HTTPS autorisé, buckets privés, credentials secrets, origine frontend exacte, secret HMAC quotas, environnement, pool. Valeurs manquantes/invalides : démarrage refusé. `.env.example` ne contient que placeholders. Secrets fournis par environnement ; jamais renvoyés dans health/errors/logs.

Nginx Proxy Manager seul expose API et upload MinIO en TLS ; DB et administration MinIO restent privés. Seuls les proxies configurés sont autorisés à fournir l'IP client ; les en-têtes forwarding arbitraires sont ignorés. CORS exact sur l'origine frontend, credentials autorisés, méthodes déclarées, jamais `*`. MinIO CORS autorise uniquement POST depuis cette origine ; aucun listing public. Tests locaux peuvent utiliser HTTP sur loopback avec configuration explicite de cookies non Secure ; cette dérogation est interdite hors environnement test/local.

Deux workers API initialement, chacun pool SQL 5 + overflow 5, timeout acquisition 3 s : maximum 20 connexions API ; PostgreSQL budget total 40, dont migrations et exploitation. Ces nombres sont hypothèses A01 à mesurer Q02. Timeout DB statement 3 s ; API JSON 10 s ; validation fichier 30 s ; lecture streaming 120 s, concurrence validation 2 par instance et téléchargement 20 par instance (excès 503). Les quotas globaux restent partagés DB. Aucun fichier uploadé sur disque du conteneur : traitement en flux ou mémoire bornée à 128 MiB par validation, arrêt si dépassement.

Logs structurés : request_id, route normalisée, status, durée, code d'erreur ; exclure corps, mots de passe, cookies, CSRF, coordonnées privées, URLs présignées et paramètres secrets. Aucune stack trace publique. Audit des échecs validation/publication avec identifiants et codes, sans contenu de fichier.

## Santé et bootstrap

F02 crée `app/main.py` minimal exportant `app`, sans route métier ni import de tables/migrations futures. `GET /health/live` → 200 `{"status":"ok"}` si processus vivant ; `GET /health/ready` → 200 `{"status":"ready"}` si `SELECT 1` et accès aux deux buckets privés réussissent, sinon 503 erreur `DEPENDENCY_UNAVAILABLE`. Ce contrôle ne requiert aucune table métier : F02 peut démarrer avant M01. X01 ajoute le contrôle de révision Alembic attendue à readiness (503 `SCHEMA_NOT_READY`) et assemble les routes. Health ne révèle ni version, ni secrets.

Compose F02 : services `api`, `db`, `minio`, initialisation idempotente des buckets privés ; volumes DB/MinIO nommés persistants ; healthchecks DB, MinIO et API ; démarrage API après dépendances saines. Pas de migration automatique au démarrage multiworker ; exécution unique explicite par mission migrations/D01. Tests de redémarrage prouvent la persistance sans supprimer les volumes partagés.

## Critères mesurables

La [matrice QA](contracts/verification.md) définit commandes applicables par stade, scénarios, charge et restauration. A01 n'exécute aucun test applicatif : il n'existe encore aucun code. Les seuils sont des critères futurs, jamais des résultats constatés.

Préflight QA communiqué : Python 3.13 et `uv` disponibles ; le `python` par défaut est 3.11, à éviter. Les futures commandes utilisent `uv run --python 3.13`. F01 n'a ni Compose ni Dockerfile : seuls les contrôles Python et DB avec une base de test fournie s'appliquent ; `docker compose config/build` commencent en F02. Le serveur Docker est inaccessible dans la sandbox, diagnostic externe en cours : ni Docker ni capacité VPS validés. L'absence d'un artefact prévu à une mission ultérieure est sans objet ; l'absence d'une dépendance nécessaire au test de la mission courante est un blocage à signaler, pas un test réussi.

Risques résolus par décision : cycle bootstrap F02/X01 (A01-09), migrations avant modèles (DDL autonome), publication avant validation (machine d'état et copie immuable), remplacement d'upload après validation (clé validée différente), fuite contacts (projection unique), quotas multiworker (DB atomique), faux reset (503 sans lookup), collision migrations (propriétaire séquentiel). Risques opérationnels à prouver : coût Argon2/validation et charge VPS Q02, restauration B01 ; l'absence de preuve bloque la livraison MVP, pas la rédaction A01.
