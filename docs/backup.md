# Sauvegarde et restauration

Outillage : `ops/backup/`. Configuration : copier `ops/backup/backup.env.example` vers un
fichier non suivi, remplacer chaque placeholder, `chmod 600`. Aucun script ne contient de
valeur par défaut pour un identifiant ; tout est lu dans l'environnement.

## Contenu d'un jeu de sauvegarde

`backup.sh` produit un répertoire `$BACKUP_ROOT/<horodatage UTC>` autodescriptif :

| Fichier | Rôle |
|---|---|
| `db.dump.enc` | dump PostgreSQL format `custom`, chiffré |
| `objects.tar.enc` | archive des objets MinIO, chiffrée |
| `objects.sha256` | empreinte de chaque objet capturé |
| `rowcounts.tsv` | nombre de lignes par table au moment du gel |
| `manifest.json` | révision Alembic, version serveur, images, buckets, compteurs, empreintes |
| `SHA256SUMS` | empreinte des cinq fichiers ci-dessus, vérifiée avant publication |

Un jeu incomplet n'est jamais publié : le piège de sortie supprime le répertoire partiel et
le script sort en erreur. `rotate.sh` applique ensuite la rétention.

## Cohérence entre PostgreSQL et MinIO

Le conteneur d'API détient toutes les mutations et le nettoyage horaire du portfolio.
`BACKUP_FREEZE=1` l'arrête le temps du dump : le point de sauvegarde est alors atomique et
`manifest.json` enregistre `consistency: frozen-api` ainsi que `freeze_seconds`.

Pour raccourcir l'indisponibilité, les objets sont copiés **deux fois** : une passe à chaud
avant le gel, puis une passe incrémentale après le dump. Les objets finaux étant immuables et
les clés jamais réutilisées, la première passe ne peut qu'omettre des objets écrits ensuite,
que la seconde rattrape. La fenêtre de gel se limite donc au dump plus un miroir incrémental.

`BACKUP_FREEZE=0` conserve le service en ligne et le point **n'est pas atomique** : la fenêtre
d'incohérence couvre toute la durée de l'exécution. Le mode est journalisé en avertissement et
inscrit au manifeste comme `online-nonatomic`. À n'utiliser qu'en connaissance de cause.

Garde-fou : le nombre d'objets validés capturés doit être supérieur ou égal au nombre de lignes
`portfolio_items` portant un `object_key`. Sinon la sauvegarde échoue comme incomplète.

## Rétention

`BACKUP_KEEP_DAILY` (défaut 7) et `BACKUP_KEEP_WEEKLY` (défaut 4) : le jeu le plus récent de
chacun des derniers jours, puis de chacune des dernières semaines ISO, est conservé.
`rotate.sh --dry-run` affiche la décision sans rien supprimer. La rotation refuse de
s'exécuter si elle ne conserverait aucun jeu, et `BACKUP_ROOT` doit être hors des volumes de
production.

## Restauration

La restauration ne vise **jamais** la production. `ops/backup/restore-stack.yaml` fournit une
pile jetable ; `RESTORE_CONFIRM_ISOLATED=yes` est obligatoire et toute cible ressemblant à la
production est refusée.

```bash
docker compose -f ops/backup/restore-stack.yaml up -d
ops/backup/restore.sh "$BACKUP_ROOT/<jeu>"
ops/backup/verify-restore.sh "$BACKUP_ROOT/<jeu>"
```

`restore.sh` vérifie `SHA256SUMS`, déchiffre, recontrôle l'empreinte de chaque archive contre
le manifeste, valide la table des matières du dump, refuse une base cible non vide sauf
`RESTORE_ALLOW_NONEMPTY=yes`, recrée exactement les buckets que le jeu contient, puis
revérifie `objects.sha256` après extraction. Il affiche sa durée pour la mesure du RTO.

## Vérification d'une restauration

Un export ne vaut pas une preuve. `verify-restore.sh` échoue sauf si, sur la pile restaurée :

1. `SHA256SUMS` du jeu de référence est intact ;
2. la révision Alembic restaurée est exactement celle du manifeste ;
3. les comptages par table sont identiques à `rowcounts.tsv` ;
4. **chaque** objet référencé par `portfolio_items.object_key` est récupérable depuis le
   bucket validé **et** son sha256 réel égale celui enregistré en base ;
5. le nombre d'objets vérifiés égale `referenced_objects` du manifeste.

Il publie aussi la répartition des états portfolio restaurés. Le saut de l'étape 4 exige
`VERIFY_ALLOW_NO_PORTFOLIO=yes`, réservé à un schéma antérieur à O01, et est journalisé.

## RPO et RTO

**Non mesurés.** Les cibles A01 (`docs/architecture.md`) restent des objectifs, pas des
mesures. Aucun démon Docker, aucun PostgreSQL et aucun MinIO n'existe sur le poste de
développement : la répétition réelle sauvegarde → restauration → vérification n'a jamais été
exécutée. Le RPO effectif découle de la fréquence choisie dans `schedule.example` ; le RTO se
lit dans les durées que `restore.sh` et `verify-restore.sh` affichent lors de la première
répétition réelle. Tant que cette répétition n'a pas eu lieu, cet outillage est **non
vérifié** : voir `docs/missions/B01.md` et GAP-12 de `docs/deployment-gaps.md`.

## Contrôles statiques disponibles

`ops/backup/check.sh` analyse chaque script, vérifie la limite de longueur, lance
`shellcheck` s'il est présent et rend `restore-stack.yaml` avec des valeurs d'exemple. Il
signale explicitement tout contrôle non exécuté au lieu de le compter comme réussi.
