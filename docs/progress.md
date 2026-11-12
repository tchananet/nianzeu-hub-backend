# Reprise A01 — prêt pour revue QA, non validé

Date : 2026-11-12. Exécutant : Architect. Worktree : E:/Dev/nianzeuhub-main/nianzeuhub-main/worktrees/A01. Branche : docs/a01-architecture. Base : 2d64a56bc9f8e6c48b8bf994bfbf6ab9b122b2d7. Aucun code applicatif, frontend, fusion, push ou déploiement effectué. Ne pas démarrer F01 avant QA indépendante positive et fusion A01 par responsable habilité.

## Livrables et commits contrôlés

| SHA | Intention / fichiers |
|---|---|
| 0fea0f5d2b416caf476d1a27375a62b83ab86570 | Architecture et ownership ; AGENTS.md copié sans modification |
| d4cb90ff8042c5baadf0ace6d01c192aa1fb2828 | Six contrats v1 : HTTP, identité, profils/contact/recherche, portfolio, données/migrations, vérification |

Le commit qui ajoute ce suivi est le candidat final : résoudre son SHA exact avec `git rev-parse HEAD`, également fourni dans la remise conversationnelle. Pas d'auto-référence fictive au SHA du document lui-même. QA doit relire ce candidat entier, pas seulement le commit de contrats.

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
