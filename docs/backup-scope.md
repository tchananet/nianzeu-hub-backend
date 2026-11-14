# Périmètre de sauvegarde des objets

Les deux buckets vivent dans **SeaweedFS**, dont la passerelle S3 est le seul point d'accès
aux objets (`storage:8333` dans le réseau de la pile). Le raisonnement ci-dessous porte sur le
contenu des buckets, pas sur le moteur : il resterait identique avec une autre implémentation
S3. Le client de copie est `rclone` (voir `docs/backup.md`).

## Bucket validé : toujours sauvegardé

Il contient les objets finaux immuables du portfolio. Chaque ligne
`portfolio_items` à l'état `validated` ou `published` référence un `object_key` et porte le
`sha256` attendu. Ces objets sont irremplaçables : perdus, les éléments de portfolio publiés
deviennent des références mortes que le talent devrait re-téléverser. Ils sont donc dans le
périmètre, et la vérification de restauration les contrôle un par un.

## Bucket de quarantaine : hors périmètre par défaut

`BACKUP_INCLUDE_QUARANTINE=0` par défaut. Justification :

- La quarantaine ne contient que des téléversements en cours de validation. Le contrat
  `docs/contracts/portfolio.md` fixe l'expiration du formulaire présigné à cinq minutes et le
  nettoyage O01 supprime les objets de quarantaine de plus de 24 heures.
- Un objet de quarantaine n'est jamais lisible publiquement et ne devient final que recopié
  sous une nouvelle clé immuable, avec recalcul du sha256. Le fichier final est donc déjà
  couvert par le bucket validé.
- Restaurer de la quarantaine ressusciterait des réservations de quota et des états `pending`
  ou `validating` sans objet cohérent, que le nettoyage effacerait immédiatement.

Conséquence assumée : un téléversement en cours au moment de la sauvegarde est perdu. Le
talent le relance ; aucune donnée publiée ne disparaît.

`BACKUP_INCLUDE_QUARANTINE=1` reste possible pour une investigation. Le manifeste enregistre
le choix sous `quarantine_included`, et `restore.sh` recrée les buckets d'après le manifeste
et non d'après la configuration de l'opérateur, pour ne jamais fabriquer un bucket vide que
la sauvegarde n'a pas capturé.

## Ce qui n'est pas sauvegardé

- Les secrets. Ils vivent dans l'environnement de déploiement, jamais dans un jeu de
  sauvegarde. Une restauration exige de les fournir à nouveau.
- Les fenêtres de quotas (`rate_limit_windows`) et la déduplication de vues
  (`profile_view_dedup`) sont des données d'entretien à durée de vie courte. Elles sont dans
  le dump parce qu'elles appartiennent au schéma, mais leur perte est sans conséquence.
- Les images Docker. Le manifeste enregistre leurs empreintes (`pg_image`,
  `object_client_image`, `api_image`) pour reconstruire un environnement équivalent, mais les
  couches elles-mêmes proviennent du registre.
- Le fichier d'identités S3 de SeaweedFS. Il est reconstruit à chaque démarrage depuis
  l'environnement, en production comme sur la cible de restauration ; il n'existe donc ni dans
  un jeu de sauvegarde ni dans le dépôt.
