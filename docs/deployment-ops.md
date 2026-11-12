# Déploiement — migrations et tâches planifiées

Annexe de [deployment.md](deployment.md). Procédures dérivées de `migrations/env.py`,
`alembic.ini`, `Dockerfile`, `docker-compose.yml` et `contracts/portfolio.md` au SHA
`6e827ff`. **Aucune de ces commandes n'a été exécutée par D01** : elles sont à reproduire
et à consigner par la mission autorisée à déployer.

Procédures de déploiement proprement dites : [deployment-procedures.md](deployment-procedures.md).

## État réel du schéma

Chaîne présente : `0001_identity` → `0002_profiles`. `alembic heads` doit donc renvoyer une
seule tête, `0002_profiles`. La révision `0003_portfolio_search` prévue par M03 dans
`contracts/data.md` **n'existe pas** dans `migrations/versions/` : les tables `portfolio_items`
et `portfolio_uploads` et les index de recherche ne sont pas créés (GAP-09).

## Comment les migrations sont appliquées

- `alembic.ini` ne contient aucune URL ; `migrations/env.py` lit `APP_DATABASE_URL` dans
  l'environnement et refuse tout ce qui n'est pas `postgresql+psycopg` sans option de requête.
- Le mode hors ligne est explicitement refusé : `alembic upgrade --sql` est impossible, il faut
  une PostgreSQL réelle. DDL transactionnel, `lock_timeout=3000`, `connect_timeout=3`, `NullPool`.
- **L'image runtime ne contient ni `alembic.ini` ni `migrations/`** : le `Dockerfile` ne copie
  que `pyproject.toml`, `uv.lock` et `app/` (plus `tests/` au stage `test`). Le paquet `alembic`
  est installé, mais les scripts de révision sont absents : aucune migration ne peut être lancée
  depuis les conteneurs `api` ou `buckets` tels quels (GAP-11).
- **Aucun service Compose n'applique de migration** et A01 interdit la migration automatique au
  démarrage multiworker : c'est une étape manuelle, unique, explicite, exécutée une seule fois
  par déploiement, jamais en parallèle de deux instances.
- `db` ne publiant aucun port, l'hôte ne joint pas PostgreSQL directement. Monter les scripts
  dans un conteneur jetable rattaché au réseau du projet, depuis un checkout au SHA déployé :

```bash
PROJECT=nianzeuhub          # COMPOSE_PROJECT_NAME réel
IMAGE=$(docker compose images -q api)   # image effectivement déployée
docker run --rm --network "${PROJECT}_default" \
  -v "$PWD/alembic.ini:/opt/app/alembic.ini:ro" \
  -v "$PWD/migrations:/opt/app/migrations:ro" \
  -e APP_DATABASE_URL="postgresql+psycopg://app:<MOT_DE_PASSE>@db/app" \
  "$IMAGE" alembic current        # puis: alembic heads, puis: alembic upgrade head
```

Vérifier `alembic heads` (exactement une tête) **avant** `upgrade head`, relever
`alembic current` avant et après, et consigner la révision atteinte dans le journal de
livraison. Un `upgrade` qui échoue laisse la révision inchangée grâce au DDL transactionnel,
mais ne tente jamais de `downgrade` automatique.

- **Pas de retour arrière automatique de schéma.** `contracts/data.md` réserve les downgrades
  destructifs aux bases jetables : ils suppriment les objets introduits par la révision et
  perdent leurs données. Voir la procédure honnête dans
  [deployment-procedures.md](deployment-procedures.md).

## Nettoyage portfolio — planification horaire

Commande contractuelle (`contracts/portfolio.md`, décision A01-06), idempotente et à exécuter
**une seule instance à la fois**, dans le conteneur API où le venv est déjà sur le `PATH` :

```bash
docker compose exec -T api python -m app.modules.portfolio.cleanup --once
```

Planification : **toutes les heures**, depuis l'hôte, car le conteneur API est `read_only` et
ne contient aucun planificateur. Timer systemd `OnCalendar=hourly` avec
`RandomizedDelaySec=300`, ou cron horaire, dans les deux cas encadré par
`flock -n /run/lock/nianzeuhub-cleanup` et un `timeout` dur pour interdire tout recouvrement.

Effets attendus : expiration des réservations et des `pending` périmés, passage en `rejected`
des `validating` dont le bail a expiré, suppression des objets de quarantaine de plus de 24 h
et des objets finaux non référencés de plus de 24 h après nouvelle vérification en base.
PostgreSQL indisponible → **aucune suppression** ; les clés ne sont jamais réutilisées.

Supervision : code de sortie non nul à journaliser et alerter, jamais à réessayer en boucle
serrée. Les journaux de la commande sortent sur la sortie du conteneur `api`.

**Limitation actuelle** : `app/modules/portfolio/` n'existe pas (mission O01 non commencée).
La planification ci-dessus est donc définie mais **non activable** aujourd'hui ; l'activer
telle quelle produirait un échec horaire. Voir GAP-09.

## Autres entretiens prévus et non planifiés

`contracts/data.md` impose aussi la purge des fenêtres de quota de plus de 24 h, la
déduplication des vues de plus de 48 h et l'agrégation au-delà de 90 jours.
`app/core/quotas.py::purge_expired` existe et est exposé par
`IdentityLimits.purge()` (`app/modules/identity/limits.py`), mais **aucun appelant planifié
n'existe dans le dépôt** : en l'état, `rate_limit_windows` et `profile_view_dedup` croissent
sans borne. Aucune commande d'entretien n'est fournie pour ces tables ; il n'y a donc rien à
planifier aujourd'hui sans une mission dédiée (GAP-10).
