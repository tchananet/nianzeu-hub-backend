# Suivi global — candidat intégré F01, revalidation QA requise

## Intégration candidate du 2026-11-12 — aucune fusion main

Branche `test/f01-integration-remote`, worktree `worktrees/F01-INTEGRATION`,
base main `86822068afe71d7a0116d2267c13785a6b64c1d2`.
Intégration --no-ff de F01 `6d3cd45cb4f9b7685cbda06bf4ecaf9207d44c05`,
puis du harness `a75fcfc1f88a3d3b1d8fafc6d1d09b2204d7cdd5`.
Seul conflit résolu : ce suivi ; code applicatif et CORS inchangés.
Le parent signale stack distante isolée 101 en cours : lock, PyAV, Ruff et Mypy
réussis à ce stade ; aucune réussite pytest ni validation finale déduite ici.
La stratégie distante autorisée ci-dessous reste applicable ; endpoint identifié par
le parent : 3 diddifree-prod. Services/domaines de production hors périmètre.
Publication de cette seule branche candidate autorisée pour test du SHA intégré exact.
Le harness versionné cible encore le SHA F01 original : le parent doit fournir le SHA
intégré exact dans le Compose soumis au test (fetch, assertion et marqueur), consigner
ce Compose et utiliser une nouvelle stack/volume. Ne pas tester implicitement une branche.
QA indépendante doit revalider ce SHA avant acceptation F01 ; main reste inchangé.
Tout changement CORS ultérieur par l'Architect imposera une nouvelle revalidation.

## Historique stratégie distante — état transmis le 2026-11-12

Données communiquées par l'orchestrateur, non remesurées ni reproduites par cette mission documentaire ; elles actualisent le suivi historique conservé ci-dessous.

- A01 : revue QA `e7a7b2c`, fusion `9ae4a0d`.
- F01 : branche `feat/f01-foundations`, SHA `6d3cd45`, revue QA `7d49b65` ; 51 tests réussis, 2 erreurs DB, 0 skip. Code JSON corrigé ; blocages restants : DB et PyAV lié à l'espace disque. F01 non validée, fusion bloquée.
- E: libre : mesure actuelle transmise de 26 MB ; aucune nouvelle mesure effectuée ici.
- Choix utilisateur : tests Docker plus tard ou directement sur stack Portainer `diddifree` dédiée et isolée de test ; Docker local reste une option. URL d'accès et endpoint inconnus, aucun accès acquis ni environnement validé. Production interdite.
- Reprise : identifier la cible de test, vérifier accès et isolation avant exécution ; obtenir la preuve PostgreSQL réelle obligatoire (pas SQLite), résoudre le blocage PyAV/disque, puis faire reproduire les contrôles applicables par QA au SHA exact. Tout report reste bloquant, sans succès anticipé ni levée des conditions de fusion ; F02 attend la fusion F01 et conserve son exigence de reproductibilité locale.

Mission présente : Architect documentaire, branche `docs/deferred-container-tests`, worktree `worktrees/test-strategy` ; ownership limité à `plan.md`, `docs/contracts/verification.md` et ce suivi. Aucun code, infrastructure, `.env`, accès distant ou changement de stack ; aucun merge/push. Ce suivi ne remplace pas les rapports QA.

## Historique remise F01 — corrigé, réexamen QA alors en attente

Mise à jour Backend F01 autorisée le 2026-11-12. A01 : **VALIDÉ par QA** au candidat
`e7a7b2c`, rapport `42c9a9f`, fusion main `9ae4a0d607f5a048ecf64c2ad095fd162a079e57`.
F01 : QA `4b823ce` a bloqué le candidat `d734912` pour CODE-01 et deux blocages environnementaux.
CODE-01 corrigé par Backend, **réexamen QA en attente**, aucune auto-validation.
SHA correction testé : `7571f40f6f2e2be7d2f7f9c5fd129b537233c9af`.

Compteurs : Ruff/Mypy/diff verts ; 51 tests unitaires réussis, dont 6 régressions encodage JSON ;
2 tests PostgreSQL en erreur explicite faute de `TEST_DATABASE_URL`, 0 skip.
Suite complète : 51 réussis, 2 erreurs, sortie 1. 25 fichiers Python, maximum 92 lignes.
7 commandes de contrôle : 4 sorties 0, 3 sorties 1 (DB seule, suite complète, sync offline check).
Installation complète bloquée aussi par espace disque E: insuffisant : 50 paquets locaux,
PyAV verrouillé mais non installé. Ce n'est pas une installation complète validée.

Reprise : libérer l'espace nécessaire sous responsabilité du propriétaire, fournir une PostgreSQL
de test locale autorisée, relancer sync verrouillé et tous les contrôles ; QA doit réexaminer CODE-01.
Commandes exactes, microcommits, ownership, limites et journal dans [F01](missions/F01.md).
F02 et toutes les suites **non commencées**. Aucun merge/push/déploiement par F01.

## Archive de la remise auteur A01 avant revue (historique)

Le texte ci-dessous décrit la remise initiale ; son ancien état « non validé » est remplacé
par le verdict et la fusion A01 ci-dessus. Ses preuves historiques restent conservées.

Date : 2026-11-12. Exécutant : Architect. Worktree : E:/Dev/nianzeuhub-main/nianzeuhub-main/worktrees/A01. Branche : docs/a01-architecture. Base : 2d64a56bc9f8e6c48b8bf994bfbf6ab9b122b2d7. Aucun code applicatif, frontend, fusion, push ou déploiement effectué. Ne pas démarrer F01 avant QA indépendante positive et fusion A01 par responsable habilité.

## Livrables et commits contrôlés

| SHA | Intention / fichiers |
|---|---|
| 0fea0f5d2b416caf476d1a27375a62b83ab86570 | Architecture et ownership ; AGENTS.md copié sans modification |
| d4cb90ff8042c5baadf0ace6d01c192aa1fb2828 | Six contrats v1 : HTTP, identité, profils/contact/recherche, portfolio, données/migrations, vérification |

Le HEAD remis, incluant ce suivi et son dernier diagnostic, est le candidat final : résoudre son SHA exact avec `git rev-parse HEAD`, également fourni dans la remise conversationnelle. Pas d'auto-référence fictive au SHA du document lui-même. QA doit relire ce candidat entier, pas seulement le commit de contrats.

Fichiers à examiner : [architecture](architecture.md), [ownership](ownership.md), [HTTP](contracts/http.md), [identité](contracts/identity.md), [profils](contracts/profiles.md), [portfolio](contracts/portfolio.md), [données](contracts/data.md), [vérification](contracts/verification.md), [AGENTS](../AGENTS.md), ce suivi. README et plan non modifiés. Specs originales lues à ../../specs.md depuis racine A01 ; baseline documentaire, aucune compatibilité parfaite avec code existant affirmée.

## Décisions remises

Contrats API v1 stricts, sessions opaques PostgreSQL/CSRF/Origin, quotas atomiques, reset 503 sans faux succès ; profils publics avec contacts privés par défaut, email public nullable distinct du login ; enums Frontend conservés, dates complètes avec fin null, tarif XAF/unité explicite. photoHint cosmétique, useInternalForm et portfolio link hors MVP.

Uploads privés avec réservation, validation réelle, copie finale immutable et publication explicite ; suppression/depublication retire nouvelles lectures. Registre M01 → M02 → M03 unique ; DDL avant modèles, aucun module ne crée sa migration. F02 possède app/main.py pour health sans tables métier ; gel après F02 puis transfert X01 pour intégration. Frontend explicitement consultatif, quatre rôles préservés.

## Preuves auteur réellement exécutées

Avant chacun des deux commits ci-dessus : `git diff --check` et `git diff --cached --check`, sorties 0 ; diff staged/stat inspecté, chemins ciblés uniquement. Au SHA d4cb90ff8042c5baadf0ace6d01c192aa1fb2828 :

- `git diff 2d64a56bc9f8e6c48b8bf994bfbf6ab9b122b2d7 HEAD --check` : sortie 0.
- `git status --short` : sortie 0, vide.
- Boucle PowerShell sur `git diff --name-only <base> HEAD` : 9 fichiers conformes (AGENTS.md, architecture, ownership, six contrats), aucun source/test applicatif ; limite de lignes source sans objet.
- Résolution PowerShell des liens Markdown locaux via Test-Path : 11 liens existants, aucun manquant.
- `Get-FileHash AGENTS.md` et `Get-FileHash ../../backend/AGENTS.md` : SHA256 identique DCD691A30BC4B82BEA74C719B1BCEA7DF72C5AC39FD69441941DF038E644497F ; recherche Architect/Backend/Frontend/QA positive.

Le suivi ajoute un dixième fichier documentaire ; contrôler à nouveau le candidat final après commit, avec les commandes ci-dessous. Aucun test Python, PostgreSQL, Docker ou VPS exécuté par Architect. Les seuils de verification.md sont des critères futurs, pas des mesures.

## Environnement et blocages transmis

Préflight communiqué par QA : Python 3.13 et uv disponibles ; python par défaut 3.11 à éviter. Docker local inaccessible/ne démarre pas, diagnostic hors sandbox en cours, non résolu ici. Ni Docker ni VPS validés. En F01, pas de Dockerfile/Compose attendu : commandes Compose sans objet ; tests DB restent bloqués si aucune PostgreSQL locale accessible, sans substituer SQLite ni compter skips comme succès. Les tests unitaires disponibles peuvent avancer, mais la preuve DB est nécessaire à la validation F01.

Dernier retour QA à la remise : service Docker local stopped ; Start-Service échoue faute de droits Windows ; utilisateur notifié en async ; aucun PostgreSQL local trouvé. Les tests DB F01 sont donc actuellement **bloqués**, et non simplement en attente de vérification de disponibilité. Ce diagnostic est transmis par QA, pas exécuté par Architect.

## Prochaine action autorisée

QA indépendant : prendre le SHA final remis dans son worktree QA sous workspace, relire cohérence/ownership et contrats, reproduire les contrôles documentaires, consigner commandes exactes/codes/verdict dans docs/qa/A01.md (propriété QA). Le présent fichier est un suivi auteur et ne remplace pas ce rapport. En cas de correction, Architect reste dans ses chemins et remet un nouveau SHA ; tests/revue concernés à reprendre. Aucune fusion par cette mission.

Commandes documentaires de reprise (PowerShell, racine worktree) :

```powershell
git branch --show-current
git rev-parse HEAD
git status --short
git diff 2d64a56bc9f8e6c48b8bf994bfbf6ab9b122b2d7 HEAD --check
git diff --name-only 2d64a56bc9f8e6c48b8bf994bfbf6ab9b122b2d7 HEAD
Get-FileHash AGENTS.md
Get-FileHash ../../backend/AGENTS.md
```

Après QA et fusion autorisée seulement : fiche F01 avec nouveau SHA main, worktree distinct, chemins exclusifs et disponibilité PostgreSQL consignée ; lire architecture et six contrats avant implémentation. Aucune installation externe de skill : create-tech-spec déjà déclaré indisponible, plan approuvé exécuté directement.
