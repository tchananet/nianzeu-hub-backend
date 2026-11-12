# Ownership et fiches de mission

## A01

Rôle exécutant : Architect. Branche `docs/a01-architecture`, worktree `E:/Dev/nianzeuhub-main/nianzeuhub-main/worktrees/A01`, base `2d64a56bc9f8e6c48b8bf994bfbf6ab9b122b2d7`. Dépendance : aucune. Livrables exclusifs : `docs/architecture.md`, `docs/contracts/*`, ce fichier, `docs/progress.md` (extension explicitement autorisée par la mission). `AGENTS.md` est ajouté tel que copié du backend, sans modification ; ses quatre rôles Architect, Backend, Frontend, QA sont préservés. L'orchestrateur coordonne ; l'exécution courante est la mission Architect autorisée.

Critères A01 : API/données et sécurité testables, registre migrations, bootstrap F02 sans dépendance X01, commandes QA adaptées, provenance des décisions, diff propre, aucun code. Remise **prête pour revue**, jamais validation autoattribuée. QA indépendant possède `docs/qa/A01.md` et teste le SHA remis. Aucun merge/push/deploy autorisé ici.

## Attribution des suites (à confirmer par fiche avant départ)

Tous les chemins sont relatifs à la racine du dépôt backend, qui est ici la racine du worktree ; ne pas créer un second répertoire `backend/`.

| Mission | Propriétaire / chemins exclusifs | Prérequis fusionnés |
|---|---|---|
| F01 | Backend fondations : `pyproject.toml`, lock choisi, `app/core/`, `app/shared/`, `tests/core/` | A01 |
| F02 | Backend infra : `Dockerfile`, `docker-compose.yml`, `.env.example`, `tests/infra/` ; **`app/main.py` temporaire health uniquement** | F01 |
| M01 | Backend migrations désigné : `alembic.ini`, `migrations/`, `tests/migrations/` | F02 |
| I01 | Backend identité : `app/modules/identity/`, `tests/identity/` | F02, M01 |
| M02 | Même propriétaire migrations : `migrations/`, `tests/migrations/` | I01 |
| P01 | Backend profils/contact : `app/modules/profiles/`, `app/modules/contact/`, `tests/profiles/`, `tests/contact/` | I01, M02 |
| M03 | Même propriétaire migrations : `migrations/`, `tests/migrations/` | P01 |
| R01 | Backend découverte : `app/modules/discovery/`, `tests/discovery/` | M03 |
| O01 | Backend portfolio : `app/modules/portfolio/`, `tests/portfolio/` (inclut nettoyage) | M03 |
| X01 | Backend intégration : **`app/main.py` transféré de F02**, `tests/api/` | R01 et O01 |
| Q01 | QA : `tests/security/`, `docs/qa/security.md` | X01 |
| Q02 | QA : `tests/load/`, `docs/qa/load.md` | Q01 + VPS de test autorisé |
| B01 | Backend sauvegarde : `ops/backup/`, `docs/backup.md` | Q01 |
| D01 | Architect : `docs/deployment.md`, `docs/qa/release.md` (synthèse, verdict signé par QA) | Q02 et B01 |

Extension A01 : `tests/migrations/` est attribué au propriétaire migrations pour ne pas laisser les preuves de M01/M02/M03 sans propriétaire. `alembic.ini` reste à ce même propriétaire tout au long des trois missions. Aucun agent de module n'y écrit.

Le transfert `app/main.py` est décidé ici : F02 peut le créer et le tester pour health, son ownership se termine après sa fusion ; fichier gelé durant M01 à O01 ; X01 en devient seul propriétaire au départ de sa mission. X01 conserve health, ajoute readiness schéma et assemble les routeurs. F02 n'attend pas X01. Tests de routeurs I01/P01/R01/O01 via apps de test locales, pas d'édition de main. Un correctif intermédiaire de main requiert une attribution explicite distincte.

Les marqueurs de packages Python nécessaires à un module sont sous son répertoire. Utiliser packages namespace pour les ancêtres `app/` et `app/modules/` afin d'éviter des `__init__.py` partagés sans propriétaire. Toute configuration transverse supplémentaire (CI, fixture racine, ignore) requiert attribution avant création. Une dépendance nouvelle d'O01 doit être prévue par F01 selon le contrat stockage/validation ; sinon mission fondations dédiée avant O01, pas de modification opportuniste de pyproject.

Chaque fiche de suite donne branche, worktree sous le workspace, SHA de base `main` validé, propriétaire individuel, fichiers, critères et tests applicables. Les identités des futurs agents et SHA de fusion ne sont pas inventés par A01. R01/O01 seulement en parallèle ; M01 → M02 → M03 sans branches Alembic concurrentes. QA possède exclusivement `docs/qa/<ID>.md` ; aucune édition par l'auteur.

`docs/progress.md` appartient à Architect pour cette remise A01 ; après fusion, tout transfert au coordinateur est consigné avant écriture. Les auteurs déposent leurs preuves dans leurs fiches/rapports attribués ; aucun auteur ne marque son propre travail VALIDÉ. Frontend demeure un rôle disponible mais sans mission ni chemin modifiable dans cette phase backend.

Frontend est explicitement **consultatif** : il fournit les champs et usages existants, relit la correspondance des contrats, sans modifier le frontend dans A01. Son retour sur enums, contacts, dates, tarif, photoHint, liens et formulaire interne est intégré dans `docs/contracts/profiles.md` et `portfolio.md`. Architect tranche les nouveaux choix backend ; QA vérifie indépendamment. Les quatre rôles d'AGENTS.md sont conservés.

## Taille et exceptions

Sources manuelles et tests <100 lignes ; documentation sans plafond. Registre initial : **aucune exception**, aucun fichier source ajouté A01. F01 doit faire attribuer le registre de ses exceptions ou transmettre une mise à jour documentaire Architect avant livraison : chemin exact, catégorie (généré/lock/migration), motif, outil/version et commande de génération. Une catégorie seule n'exempte aucun fichier. Les migrations manuelles bénéficient de l'exception du plan uniquement si leur chemin et leur motif sont enregistrés avec outil « rédaction manuelle Alembic » ; ce n'est pas une permission de produire des modules métier longs.
