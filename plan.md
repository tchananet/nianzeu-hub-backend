# Plan d’exécution documentaire du backend

## Périmètre et décisions
- Cette mission produit uniquement ce plan ; aucune implémentation, fusion, publication ou mise en production maintenant.
- Première mission suivante : A01, architecture et contrats uniquement ; aucun code applicatif avant sa validation et sa fusion.
- Références : `README.md` et `../specs.md` ; les contraintes ci-dessous priment sur leurs divergences.
- Monolithe modulaire Python 3.12+, FastAPI, PostgreSQL, SQLAlchemy 2.x, Alembic, Pydantic 2.x et MinIO.
- Docker Compose sur VPS derrière Nginx Proxy Manager ; HTTPS, volumes persistants PostgreSQL et MinIO.
- Dimensionnement : 500 comptes et 100 utilisateurs simultanés ; capacité à démontrer sur VPS de test, jamais présumée.
- Compte talent par défaut ; visiteurs anonymes autorisés à rechercher, lire et contacter par email, WhatsApp ou téléphone.
- Profils : expériences, certifications, compétences, localisation, disponibilité et coordonnées dont le talent choisit la visibilité.
- Portfolio public seulement après validation technique et publication ; objets non validés inaccessibles publiquement.
- Envoi d’email et reset différés : port fournisseur prévu, adaptateur désactivé avec erreur explicite ; aucune fausse réussite.
- OAuth, comptes recruteurs, messagerie interne et modération administrative hors MVP ; aucun fournisseur email à intégrer maintenant.
- Chaque fichier source manuel, tests inclus, fait au maximum 100 lignes ; découper par responsabilité.
- Exceptions : fichiers générés, fichiers lock et migrations, recensés avec chemin, motif et outil de génération ; aucune exemption implicite.

## Rôles et règles de livraison
- Orchestrateur : découpe, attribue, suit dépendances et blocages, recueille les preuves ; ne code pas et ne corrige pas les agents.
- Agent `architect` : contrats API/données, décisions de sécurité, ownership et séquencement des migrations.
- Agent `backend` : une mission bornée, ses tests et sa documentation ; respecte les contrats et les fichiers attribués.
- Agent `qa` indépendant de l’auteur : revue, reproduction des contrôles, preuve et verdict `VALIDÉ` ou `BLOQUÉ`.
- Chaque mission possède une branche distincte `docs/<id>-<objet>`, `feat/<id>-<objet>` ou `test/<id>-<objet>`, issue de `main` propre.
- Chaque agent travaille dans un worktree distinct sous `E:/Dev/nianzeuhub-main/nianzeuhub-main/worktrees/<id>`.
- Aucun fichier, clone, worktree ou artefact de mission hors de ce workspace ; aucun changement frontend.
- Avant départ : fiche de mission avec ID, propriétaire, chemins exclusifs, livrables, critères, dépendances et SHA de base.
- Les chemins partagés ont un propriétaire unique ; tout transfert d’ownership est acté avant modification.
- Micro-commits cohérents et testés : une intention par commit, aucun mélange avec une autre mission, aucun secret.
- Les contrôles ciblés passent avant chaque commit ; les contrôles complets passent avant remise à QA.
- QA consigne dans `docs/qa/<id>.md` : SHA exact examiné, environnement, commandes exactes, codes de sortie, résultats et journaux utiles.
- Une preuve référence le SHA testé, pas le commit ultérieur qui ajoute le rapport ; toute correction relance les contrôles concernés.
- QA vérifie aussi diff, ownership, limite de lignes, exceptions et respect des contrats ; un blocage interdit la fusion.
- Un responsable habilité fusionnera avec `git merge --no-ff` seulement après verdict QA positif, tests verts et zéro blocage.
- Si `main` évolue depuis la revue, tester à nouveau le candidat intégré et consigner ses SHA avant autorisation de fusion.
- Après fusion, vérifier `main` ; la vague suivante part uniquement de ce nouveau `main` propre et validé.
- Ce plan n’autorise aucun push, aucune fusion ni aucun déploiement par l’agent qui le rédige.

## Missions atomiques et critères d’acceptation
Les chemins sont relatifs au dépôt `backend` ; les tests d’un module appartiennent au propriétaire de ce module.

| ID / agent | Livrable et ownership exclusif | Critères d’acceptation | Dépendances |
|---|---|---|---|
| A01 / architect | `docs/architecture.md`, `docs/contracts/`, `docs/ownership.md` | Contrats versionnés : routes, erreurs, cookies/sessions, autorisations, schéma, filtres/pagination, uploads/publication, reset désactivé ; registre des migrations ; seuils QA et risques résolus ; aucune implémentation | Aucune ; première mission |
| F01 / backend | `pyproject.toml`, lock, `app/core/`, `app/shared/`, `tests/core/` | Configuration validée, accès PostgreSQL, ports stockage/email, erreurs explicites, tests ciblés verts et exceptions de taille documentées | A01 fusionnée |
| F02 / backend | `Dockerfile`, `docker-compose.yml`, `.env.example`, `tests/infra/` | Build et démarrage local reproductibles, healthchecks, volumes persistants, aucun secret ; pas de déploiement VPS | F01 fusionnée |
| I01 / backend | `app/modules/identity/`, `tests/identity/` | Inscription talent, login/logout/me ; hash robuste, sessions révocables, cookies sûrs, protection CSRF adaptée, limitation login et tests d’accès ; reset explicitement indisponible | F02 et M01 fusionnées |
| P01 / backend | `app/modules/profiles/`, `app/modules/contact/`, `tests/profiles/`, `tests/contact/` | CRUD propriétaire ; expériences/certifications/skills ; lecture anonyme ; visibilité contacts respectée ; accès tiers refusé | I01 et M02 fusionnées |
| M01 / backend désigné | `migrations/`, `alembic.ini` : initialisation et identité | Upgrade sur base vide, contraintes identité, aller-retour de migration testé en base jetable | F02 fusionnée |
| M02 / même rôle | `migrations/` : profils, compétences, expériences, certifications, contacts | Migration depuis M01, intégrité et conservation des données vérifiées | I01 fusionnée |
| M03 / même rôle | `migrations/` : portfolio et index recherche | Révision unique après M02 ; index et contraintes conformes aux contrats, upgrade testé sur données existantes | P01 fusionnée |
| R01 / backend recherche | `app/modules/discovery/`, `tests/discovery/` | Recherche anonyme paginée ; filtres mot-clé, skill, lieu, disponibilité, expérience ; aucune donnée privée exposée ; requêtes bornées testées | M03 fusionnée |
| O01 / backend portfolio | `app/modules/portfolio/`, `tests/portfolio/` | Images/PDF/vidéos : MIME réel, extension, taille, clés et ownership vérifiés ; refus testés ; publication après validation ; lecture publique après publication seulement | M03 fusionnée |
| X01 / backend intégration | `app/main.py`, `tests/api/` | Routes assemblées ; parcours inscription → profil → recherche → portfolio/contact vérifiés, sans réécriture des modules | R01 et O01 fusionnées |
| Q01 / qa | `tests/security/`, `docs/qa/security.md` | Contrôle indépendant sessions, accès tiers, uploads, fuite de données et reset désactivé ; preuves et aucun blocage | X01 fusionnée |
| Q02 / qa | `tests/load/`, `docs/qa/load.md` | Sur VPS de test autorisé : 500 comptes synthétiques, 100 simultanés, scénario réaliste ; p95, erreurs, débit, CPU/RAM et connexions mesurés contre seuils A01 | Q01 fusionnée et VPS de test disponible |
| B01 / backend | `ops/backup/`, `docs/backup.md` | Sauvegarde PostgreSQL + MinIO cohérente, rétention et procédure de restauration ; restauration isolée prouvée par QA, RPO/RTO mesurés contre A01 | Q01 fusionnée |
| D01 / architect | `docs/deployment.md`, `docs/qa/release.md` | Runbook Compose/Nginx Proxy Manager : TLS, secrets, réseau, migrations, santé, sauvegarde, rollback ; QA valide preuves Q02/B01 ; aucun déploiement exécuté | Q02 et B01 fusionnées |

## Vagues, parallélisme et migrations
- Ordre des vagues : A01 → F01 → F02 → M01 → I01 → M02 → P01 → M03 → (R01 ∥ O01) → X01 → Q01 → (Q02 ∥ B01) → D01.
- Une mission n’est achevée qu’après revue QA puis fusion par le responsable habilité ; attendre toutes les fusions de la vague avant la suivante.
- R01 et O01 utilisent deux branches et deux worktrees distincts ; contrats figés, aucun fichier partagé modifié.
- Pour chaque mission, QA reproduit les contrôles dans son propre worktree sous `worktrees/qa-<id>` au SHA remis.
- QA possède exclusivement `docs/qa/<id>.md` pour ses rapports de revue, en complément des chemins de missions ci-dessus.
- Un seul agent possède `migrations/` et `alembic.ini` à la fois ; M01, M02 et M03 sont strictement séquentielles.
- Aucun agent de module ne crée de migration ; toute évolution requise devient une mission dédiée et bloque les consommateurs jusqu’à sa fusion.
- Pas de branches Alembic concurrentes : une seule tête ; vérifier `alembic heads` et `alembic upgrade head` en environnement jetable.
- Toute divergence de contrat ou collision de fichier revient à l’architecte, puis à une mission distincte ; pas de correction hors ownership.

## Preuves et conditions de sortie
- A01 et les missions documentaires : revue des décisions, liens, cohérence des dépendances et `git diff --check` ; tests applicatifs sans objet, explicitement signalés.
- Implémentation : `ruff check .`, `mypy app`, `pytest`, `docker compose config` et `docker compose build`, plus tests ciblés et migrations applicables.
- QA consigne les commandes réellement exécutées et leurs résultats ; aucun succès anticipé, contrôle indisponible signalé comme blocage.
- Charge : A01 fixe durée, montée en charge, mélange de parcours et seuils p95/erreurs ; Q02 relève la configuration exacte du VPS et le SHA testé.
- Sauvegardes : QA restaure base et objets dans un environnement isolé, vérifie cohérence et accès aux fichiers ; un simple export ne suffit pas.
- Livraison MVP conditionnée aux preuves fonctionnelles, sécurité, charge et restauration ; déploiement ultérieur soumis à une mission explicitement autorisée.
