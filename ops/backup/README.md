# ops/backup — sauvegarde et restauration (mission B01)

Documentation opérateur complète : [`docs/backup.md`](../../docs/backup.md).
Ce répertoire ne contient aucun secret ; toute valeur vient de l'environnement.

| Fichier | Rôle |
|---|---|
| `backup.sh` | crée un jeu de sauvegarde chiffré, vérifié, puis fait tourner la rétention |
| `restore.sh` | restaure un jeu dans la pile jetable ; refuse une cible de production |
| `verify-restore.sh` | prouve la restauration : révision Alembic, comptages, objets + sha256 |
| `rotate.sh` | rétention 7 quotidiennes + 4 hebdomadaires ; `--dry-run` disponible |
| `check.sh` | contrôles statiques seulement : `bash -n`, limite de lignes, lint, Compose |
| `restore-stack.yaml` | pile jetable PostgreSQL + SeaweedFS isolée pour la répétition |
| `backup.env.example` | gabarit d'environnement, placeholders uniquement |
| `schedule.example` | crontab quotidien avec verrou partagé avec le nettoyage horaire |
| `lib/` | une responsabilité par fichier : commun, config, crypto, pg, objets, gel, manifeste |

Prérequis hôte : `docker`, GNU `coreutils` (`sha256sum`, `date -u -d`, `du -sb`),
`findutils` (`find -printf`), `tar`, `openssl`, `bash` ≥ 4.3.
Aucune installation Python ni dépendance applicative n'est requise.

Les accès PostgreSQL et S3 passent par des conteneurs jetables : `postgres:16-alpine`
et `rclone/rclone:1.76.0` (`BACKUP_OBJECT_CLIENT_IMAGE`). Le magasin d'objets est
SeaweedFS, exposé en S3 sur `storage:8333` dans le réseau de la pile. Le distant
`rclone` nommé `s3` est déclaré uniquement par des variables `RCLONE_CONFIG_S3_*` :
aucun fichier de configuration, aucun identifiant en ligne de commande.

Tous les scripts sont `set -euo pipefail`, sortent non nuls au premier doute et
suppriment un jeu incomplet au lieu de le publier.
