# Vérification par stade — critères, pas résultats

QA indépendant inscrit SHA exact, environnement, commandes réellement exécutées, codes sortie et verdict dans docs/qa/<ID>.md. Aucun test absent n'est réputé réussi. A01 est documentaire ; l'absence de runtime n'empêche pas sa revue mais interdit d'affirmer que le backend fonctionne.

## Commandes applicables

Les commandes sont exécutées à la racine du worktree de mission, dans le workspace, ou, pour les validations distantes, sur la stack de test autorisée décrite ci-dessous au SHA remis. Python QA disponible 3.13 via uv ; ne pas utiliser python par défaut 3.11. F01 doit fournir pyproject.toml et uv.lock, groupes de développement Ruff/Mypy/Pytest, outils validation et adaptateurs stockage prévus par contrats. Caches/venv/artefacts locaux de mission sous workspace ; aucune installation de skill.

| Stade | Commandes et conditions |
|---|---|
| A01 | git diff --check ; git diff --cached --check avant commit ; git diff 2d64a56bc9f8e6c48b8bf994bfbf6ab9b122b2d7 HEAD --check après commit ; git status --short ; revue liens/contrats/ownership ; aucune commande Python/Docker nécessaire |
| F01 | uv sync --locked --python 3.13 ; uv run --python 3.13 ruff check . ; uv run --python 3.13 mypy app ; uv run --python 3.13 pytest tests/core ; puis pytest complet disponible |
| F02 et suites avec artefacts Compose | docker compose config --quiet ; docker compose build ; docker compose up -d ; docker compose ps ; uv run --python 3.13 pytest tests/infra ; ne pas effacer volumes persistants de travail |
| M01/M02/M03 | uv run --python 3.13 alembic heads ; uv run --python 3.13 alembic upgrade head ; uv run --python 3.13 pytest tests/migrations ; tests de downgrade du registre uniquement DB jetable identifiée |
| I01 | uv run --python 3.13 pytest tests/identity |
| P01 | uv run --python 3.13 pytest tests/profiles tests/contact |
| R01 / O01 | uv run --python 3.13 pytest tests/discovery ou tests/portfolio respectivement |
| X01 / Q01 | uv run --python 3.13 pytest tests/api puis tests/security au stade où ce répertoire existe |

À chaque mission implémentée : Ruff/Mypy, tests ciblés puis suite existante entière (`uv run --python 3.13 pytest`) ; checks Compose à partir de F02 seulement. Aucun test d'un module futur absent n'est demandé. À F01, config/build Compose sont **sans objet**, pas en échec : ces fichiers appartiennent F02. Tests DB F01 requièrent PostgreSQL réel de test, local ou sur la stack de test autorisée, fixtures de schéma isolées ; pas de remplacement SQLite pour prétendre tester PostgreSQL.

Choix utilisateur : reporter les tests Docker ou les exécuter en Docker local ou directement sur une stack Portainer `diddifree` dédiée et isolée de test. URL d'accès et endpoint inconnus ; accès non acquis. Avant toute exécution distante, identifier la cible et vérifier l'accès et l'isolation des données, volumes, réseaux et secrets de test vis-à-vis de la production. Aucune modification de production autorisée. F02 conserve l'exigence de build et démarrage local reproductibles ; les validations peuvent s'exécuter sur cette stack autorisée, avec preuves des contrôles applicables (configuration, build, santé, persistance et tests), SHA et commandes/actions exactes consignés par QA.

Sans PostgreSQL de test accessible et preuve réelle : tests DB F01 **BLOQUÉS**, commandes unitaires possibles séparément, revue F01 non validée. Même règle pour Docker F02 et stockage O01. Les contrôles reportés restent à exécuter et bloquent la validation et la fusion ; ni skips ni résultats partiels ne constituent une suite verte. Aucun VPS, accès Portainer ou capacité Docker validé par ces documents ; état transmis et historique dans `docs/progress.md`.

## Matrice de scénarios

| Propriétaire | Preuves minimales |
|---|---|
| F01 | config invalide fail-fast ; erreurs enveloppées ; EmailPort désactivé lève ; StoragePort distingue absent/panne ; DB rollback ; quotas atomiques multi-connexion et horloge injectable |
| F02 | app health sans table métier ; dépendance arrêtée → ready 503/live 200 ; deux buckets privés ; restart conserve données ; aucun secret dans image/config versionnée |
| M01..M03 | une tête, upgrade/downgrade/re-upgrade par registre, contraintes SQL violées réellement, conservation fixtures antérieures |
| I01 | scénarios identité : cookies/rotation/expiration/révocation, CSRF/Origin, login limité, mots de passe hashés, reset 503 uniforme |
| P01 | CRUD complet et isolation A/B ; dates/null/enums/tarifs ; coordonnées masquées partout ; vues dédupliquées en concurrence |
| R01 | recherche AND/tri/pagination/bornes ; injection et caractères littéraux ; aucune coordonnée privée ; ≤5 requêtes SQL |
| O01 | machine d'état, validation réelle, overwrite présigné, quotas concurrents, récupération lease/panne, absence d'accès public avant publish, retrait après delete |
| X01 | parcours HTTP réel register → login → profil → search → upload → validate → publish → lecture anonyme → contact → unpublish → logout ; routes santé conservées |
| Q01 | reproduire attaques session/CSRF/tiers/upload/fuite/reset, sans réutiliser seulement les assertions de l'auteur |

Contrôles transverses : diff uniquement ownership ; fichiers source manuels/tests ≤99 lignes ; exceptions exactes recensées ; aucun secret/code frontend ; résultats sans trace sensible. QA vérifie les contrats via requêtes positives et négatives, pas uniquement présence de routes dans OpenAPI.

## Q02 charge — décision A01 à mesurer ultérieurement

VPS de test explicitement autorisé et isolé, configuration CPU/RAM/disques/versions/workers/pools/proxy et SHA consignés. Précharger 500 comptes synthétiques avec profils, contacts publics/privés et petits portfolios ; aucun compte réel. 5 minutes échauffement, 5 minutes montée linéaire 0→100 utilisateurs, 20 minutes à 100, 2 minutes descente. Un utilisateur attend 1..3 secondes entre parcours, sessions login au début et renouvellement seulement si nécessaire.

Mix requêtes plateau : 50% recherche, 25% profil public, 10% contacts publics, 10% lectures privées, 5% PUT profil propriétaire. Répartition IP synthétique contrôlée (100 IP au proxy de test autorisé ou 100 sources) pour ne pas confondre quota IP et saturation ; jamais confiance globale aux forwarded headers. Ne pas relever les quotas production pour ce test. Exécuter séparément scénario sécurité quotas avec IP unique et 429 attendus. Corpus et graine aléatoire consignés.

Seuils plateau : p95 lectures JSON ≤500 ms, p95 mutations ≤1000 ms ; erreurs inattendues <1% (inclut timeout, 5xx, 429 non prévus), aucune fuite ni erreur intégrité ; débit réalisé ≥25 requêtes/s, pas de diminution >20% entre première et dernière tranche 5 min. CPU moyenne <80%, RAM <85%, aucun OOM, connexions API ≤20 et total DB ≤40. Relever aussi p99, débit, nombre erreurs, CPU/RAM chaque minute. Scénario fichiers distinct : 10 utilisateurs, 20 cycles image 1 MiB, PDF 5 MiB, vidéo 20 MiB valides, validation p95 ≤30 s, aucun dépassement mémoire/erreur ; pas de prétention à 100 uploads simultanés. Tout seuil raté bloque Q02, tuning sous mission attribuée puis reprise de mesures.

## B01 restauration

RPO cible ≤24 h, RTO ≤4 h, mesurés jusqu'au parcours HTTP restauré. Sauvegarde quotidienne DB + objets cohérente : fenêtre lecture seule/mutations suspendues pendant snapshot DB et copie objets, nettoyage suspendu ; manifeste horodaté, SHA objets, révision Alembic et version application. Sauvegarde chiffrée hors volumes de production ; rétention 7 quotidiennes + 4 hebdomadaires. L'emplacement sera fixé en B01/D01 sans provisionnement A01.

QA restaure dans DB/buckets isolés, vérifie comptes/profils/contacts, intégrité hash et présence de tous objets référencés, invisibilité fichiers non publiés, connexion et téléchargement public/privé. Relever durée sauvegarde/restauration et ancienneté de snapshot réellement restaurable. Un export seul n'est pas une preuve. Aucun déploiement ni effacement production autorisé par ces critères.
