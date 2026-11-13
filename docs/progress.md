# Suivi d'exécution du backend

Document de suivi courant. Les rapports de revue indépendants restent dans `docs/qa/<id>.md`.

## État des missions

| Mission | État | Preuve |
|---|---|---|
| A01 architecture et contrats | fusionnée | `docs/qa/A01.md` |
| F01 socle `app/core` et `app/shared` | fusionnée | `docs/qa/F01.md`, `docs/qa/F01-REMOTE.md` |
| F02 Dockerfile, Compose, santé | fusionnée | `docs/missions/F02.md` |
| M01 migration identité | fusionnée | `docs/missions/M01.md` |
| I01 identité, sessions, CSRF | fusionnée | `docs/missions/I01.md` |
| M02 migration profils et contacts | fusionnée | tests `tests/migrations/profiles` |
| P01 profils et contact | fusionnée | `docs/missions/P01.md` |
| M03 portfolio et index recherche | fusionnée | `docs/missions/M03.md` |
| R01 recherche publique | fusionnée | `docs/missions/R01.md` |
| O01 portfolio | fusionnée, couverture incomplète | `docs/missions/O01.md` |
| X01 assemblage des routes | fusionnée | `docs/missions/X01.md` |
| B01 sauvegarde | fusionnée, non éprouvée | `docs/missions/B01.md`, `docs/backup.md` |
| D01 runbook de déploiement | fusionnée | `docs/deployment.md`, `docs/qa/release.md` |
| Q01 sécurité indépendante | VALIDÉ dans son périmètre | `docs/qa/security.md` |
| QA indépendante I01 | BLOQUÉ levé par décision, voir ci-dessous | `docs/qa/I01.md` |
| QA indépendante O01 | BLOQUÉ ; 3 défauts sur 6 corrigés | `docs/qa/O01.md` |
| QA indépendante M03 | VALIDÉ | `docs/qa/M03.md` |
| Q02 charge | à faire | bloquée : aucun VPS de test autorisé |

État des contrôles : `ruff` et `mypy` passent (104 fichiers source). Campagne distante sur
PostgreSQL réel au commit `f45b70b`, base fraîche : **711 réussis, 2 ignorés, 0 échec**,
sentinelle `SUITE_PASS` et code de sortie 0. Cette campagne valide les correctifs issus des
revues indépendantes (fuite de jeton de téléchargement, pièce jointe PDF par annotation,
limite de transport câblée). Les 2 ignorés sont les tests de pile F02 qui
exigent `F02_STACK_TEST=1`. En local, 460 passent et 246 se bloquent explicitement faute de
PostgreSQL ; aucun n'est jamais compté comme réussi.

## Environnement de vérification

Docker local **indisponible** : Docker Desktop n'est pas installé sur ce poste, seul le CLI
est présent. Aucun PostgreSQL local. Supabase écarté par l'utilisateur. Deux environnements
sont donc utilisés :

1. **Environnement Python isolé local** pour `ruff`, `mypy` et les tests sans base.
   L'environnement virtuel est hébergé hors du dépôt car le disque `E:` est presque plein ;
   `uv sync` dans le dépôt a échoué sur disque insuffisant.
2. **Stack Portainer jetable** pour la preuve sur PostgreSQL réel :
   `ops/test-portainer/compose.suite.yaml`, déployée sur la stack de test dédiée autorisée par
   l'utilisateur. Base en tmpfs, écoutes en loopback uniquement, aucun port publié, aucun
   volume hôte, `restart: "no"`, ressources bornées. Le runner résout `origin/main`, journalise
   le commit testé, applique les migrations puis exécute `ruff`, `mypy` et `pytest`.
   Aucune stack de production n'est touchée.

SQLite n'est jamais substitué à PostgreSQL. Les tests nécessitant une base échouent
explicitement en local avec un message de blocage ; ils ne sont jamais comptés comme réussis.

## Défauts d'intégration corrigés lors des fusions

Trois défauts réels sont apparus seulement en assemblant les branches, et sont corrigés :

1. `app/main.py` (F02) construisait `Settings()` avant que I01 n'ajoute des champs requis ;
   `mypy` signalait vingt erreurs. Le greffon `pydantic.mypy` est activé dans `pyproject.toml`,
   ce qui fait comprendre à `mypy` la construction par variables d'environnement.
2. Les répertoires de tests n'étaient pas des paquets ; après les fusions, plusieurs modules
   partageaient un même nom de base (`test_schemas.py`, `test_database.py`, …) et la collecte
   pytest échouait. Des `__init__.py` isolent désormais chaque paquet de tests.
3. Les fixtures de F01 et F02 utilisaient une origine frontend non autorisée par la politique
   d'origines introduite par I01, ce qui faisait échouer treize tests. Elles utilisent
   maintenant une origine approuvée.

## Défaut latent découvert

`tests/infra/test_health.py` construisait `S3Error` avec l'ancienne signature positionnelle.
Depuis `minio` 7.2, la réponse HTTP est le **premier** paramètre : le code d'erreur était donc
affecté à la réponse et `error.code` renvoyait `"sensitive detail"`. L'assertion censée vérifier
que la lecture de police de bucket échoue en mode fermé ne pouvait pas échouer. La construction
est corrigée par mots-clés et le contrôle est de nouveau effectif.

## Blocages ouverts

- **Q02 charge** : aucun VPS de test autorisé et dimensionné n'est disponible. Les seuils de
  `docs/contracts/verification.md` restent des critères, pas des mesures.
- **Répétition de sauvegarde B01** : exige un environnement Docker isolé, absent de ce poste.
- **MinIO réel** : les parcours portfolio sont couverts par un adaptateur de stockage factice ;
  la vérification contre un MinIO réel reste à exécuter.
- **Envoi d'email** : adaptateur volontairement désactivé, échec explicite. Hors MVP.

## Décision sur I01-01, origine non épinglée

La revue indépendante I01 a bloqué sur un écart réel : `docs/contracts/identity.md` exigeait
« exactement l'origine HTTPS configurée », alors que `app/core/origins.py` accepte une liste
close incluant tout sous-domaine `*.diddifree.com`, et que `APP_FRONTEND_ORIGIN` est validé
au démarrage sans être lu par aucun contrôle.

Arbitrage du propriétaire du produit : **conserver la liste close et corriger le contrat**
plutôt qu'épingler le contrôle. Le contrat documente la politique réelle, la confiance
accordée aux sous-domaines et le statut réservé de `APP_FRONTEND_ORIGIN`.

Risque résiduel consigné, non corrigé : un sous-domaine `*.diddifree.com` compromis franchit
le contrôle d'origine sur les mutations et sur `GET /auth/csrf`. Le jeton CSRF synchronisé et
l'absence d'intergiciel CORS (GAP-03) restent les barrières. Épingler l'origine ou ajouter
CORS serait le durcissement naturel si cette hypothèse change.
