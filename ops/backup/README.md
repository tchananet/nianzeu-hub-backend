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
| `restore-stack.yaml` | pile jetable PostgreSQL + MinIO isolée pour la répétition |
| `backup.env.example` | gabarit d'environnement, placeholders uniquement |
| `schedule.example` | crontab quotidien avec verrou partagé avec le nettoyage horaire |
| `lib/` | une responsabilité par fichier : commun, config, crypto, pg, objets, gel, manifeste |

Prérequis hôte : `docker`, GNU `coreutils` (`sha256sum`, `date -u -d`, `du -sb`),
`findutils` (`find -printf`), `tar`, `openssl`, `bash` ≥ 4.3.
Aucune installation Python ni dépendance applicative n'est requise.

Tous les scripts sont `set -euo pipefail`, sortent non nuls au premier doute et
suppriment un jeu incomplet au lieu de le publier.
