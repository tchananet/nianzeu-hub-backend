# Déploiement — premier déploiement, montée de version, retour arrière

Annexe de [deployment.md](deployment.md). **Aucune de ces procédures n'a été exécutée
par D01.** Elles ne sont applicables qu'après lever les blocages de
[deployment-gaps.md](deployment-gaps.md) et le gate de [qa/release.md](qa/release.md).

Toutes les commandes s'exécutent depuis un checkout du dépôt au SHA livré, avec
`docker compose --env-file <fichier-hors-contexte> -p <projet>` (abrégé `dc` ci-dessous).

## Premier déploiement

1. Consigner le SHA déployé, et vérifier que l'arbre de travail est propre
   (`git status --short` vide) : l'image est construite depuis ce contexte.
2. Configurer la rotation des journaux du démon Docker (GAP-06) et vérifier l'espace disque.
3. Créer le fichier d'environnement hors du contexte de build, permissions `600`, à partir de
   `.env.example`, avec `APP_ENVIRONMENT=production`, `APP_SECURE_COOKIES=true`,
   `APP_FRONTEND_ORIGIN` dans l'allowlist, `APP_STORAGE_PUBLIC_ENDPOINT` en HTTPS et des
   secrets générés indépendamment (voir [deployment-env.md](deployment-env.md)).
4. `dc config --quiet` : valide l'interpolation et révèle toute variable requise manquante.
5. `dc build` : échec attendu si une dépendance exigeait une compilation native.
6. `dc up -d --wait db minio` puis vérifier `dc ps` : les deux doivent être `healthy`.
7. `dc run --rm --no-deps buckets` ou laisser la dépendance le faire : création idempotente des
   deux buckets privés et retrait de toute policy.
8. **Appliquer les migrations** avant de démarrer l'API, selon
   [deployment-ops.md](deployment-ops.md) ; relever `alembic heads` et `alembic current`.
9. `dc up -d --wait api` ; vérifier `dc ps` (`healthy`) puis, depuis l'hôte,
   `curl -fsS http://127.0.0.1:8000/health/live` et `.../health/ready`.
10. Configurer l'hôte proxy NPM : certificat valide, redirection HTTPS, `Host` transmis,
    cible atteignable (GAP-01), et sonde `/health/live`. Vérifier depuis l'extérieur que ni
    8000, ni 9000, ni 9001, ni 5432 ne répondent publiquement.
11. Activer la planification horaire du nettoyage portfolio dès que le module existe (GAP-09).
12. Prendre une sauvegarde immédiatement après le déploiement — **procédure inexistante
    aujourd'hui** (mission B01 non livrée, GAP-12) : sans elle, l'étape 12 ne peut pas être
    tenue et aucun retour arrière de données n'est possible.

## Montée de version

1. Lire le journal de livraison : SHA actuel, révision Alembic actuelle, image en service
   (`dc images api`). Noter l'identifiant d'image : c'est le seul point de retour applicatif.
2. Sauvegarder base et objets **avant** toute migration (bloqué par GAP-12).
3. `git fetch` puis `git checkout <nouveau SHA>` ; relire le diff de `migrations/`,
   `docker-compose.yml`, `Dockerfile` et `app/core/config.py` : toute nouvelle variable
   `APP_*` requise doit être ajoutée au fichier d'environnement avant redémarrage, sinon le
   démarrage est refusé (fail-fast).
4. `dc config --quiet` puis `dc build`.
5. Appliquer les migrations avant de recréer l'API : `alembic heads` doit rester une tête unique.
   Une migration non rétrocompatible impose une fenêtre d'indisponibilité assumée — il n'y a ni
   déploiement progressif, ni double écriture, ni réplique dans ce Compose.
6. `dc up -d --wait api` puis contrôler `/health/ready`, le parcours fonctionnel attendu et les
   journaux `app.requests` (statuts, `duration_ms`).
7. Consigner nouveau SHA, nouvelle révision, nouvelle image et heure dans le journal de livraison.

Ne jamais exécuter `dc down -v`, ne jamais supprimer `postgres-data` ou `minio-data`, ne jamais
démarrer les services `tests`/`core-tests` sur l'hôte de production.

## Retour arrière — ce qui est réellement réversible

| Élément | Réversible ? | Procédure |
|---|---|---|
| Code applicatif / image | oui | repointer sur l'image ou le SHA précédent et recréer `api` |
| Configuration / variables | oui | restaurer la valeur précédente puis recréer le service |
| Objets MinIO supprimés | non | seule une restauration de sauvegarde les ramène |
| Schéma PostgreSQL migré | **non automatiquement** | voir ci-dessous |

Retour arrière applicatif seul, si et seulement si la nouvelle version n'a **pas** migré le
schéma, ou si la nouvelle révision est compatible avec l'ancien code :

```bash
git checkout <SHA précédent> && dc build && dc up -d --wait api && dc ps
```

**Schéma : aucun retour arrière automatique.** `contracts/data.md` réserve explicitement les
downgrades destructifs aux bases jetables ; un `alembic downgrade` en production supprime les
objets créés par la révision et **perd définitivement les données** qu'ils contenaient. Il
n'existe donc pas de « rollback » de migration : si l'ancien code ne tolère pas le nouveau
schéma, les seules options honnêtes sont

1. corriger en avant par une nouvelle révision (voie recommandée, sous mission migrations), ou
2. restaurer une sauvegarde cohérente base + objets, en acceptant la perte des écritures
   postérieures au point de restauration.

L'option 2 n'est pas disponible aujourd'hui : il n'existe ni `ops/backup/`, ni `docs/backup.md`,
ni restauration répétée (GAP-12). **Aucun RPO ni RTO n'est mesuré** ; les valeurs ≤ 24 h et
≤ 4 h de `contracts/verification.md` sont des cibles A01 à prouver par B01, pas des
engagements constatés. Tant que ce point reste ouvert, toute migration de production est
irréversible : à décider en connaissance de cause, pas à découvrir pendant l'incident.

Après tout retour arrière : vérifier `/health/ready`, consigner l'état atteint (SHA, image,
révision Alembic, heure, motif) et ouvrir le suivi correctif correspondant.
