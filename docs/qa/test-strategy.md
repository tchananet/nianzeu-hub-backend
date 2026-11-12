# QA documentaire — stratégie de tests

Date : 2026-11-12. Verdict : **VALIDÉ (périmètre documentaire uniquement)**.
Candidat examiné : `ba8b0d05323ee491bddb35b1fe1ca6b79d3d09fd`, base `9ae4a0d`.
Environnement : Windows / PowerShell, worktree `E:/Dev/nianzeuhub-main/nianzeuhub-main/worktrees/qa-test-strategy`, branche `test/qa-deferred-container-tests` ; HEAD initial égal au candidat, arbre propre.

## Constats

- `AGENTS.md` lu ; diff limité à `plan.md`, `docs/contracts/verification.md`, `docs/progress.md`. Aucun changement de stack ni des rôles ; ownership et dépendances conservés.
- Report des tests Docker ou exécution locale / Portainer `diddifree` de test autorisés. Endpoint et accès restent inconnus ; identification et isolation données, volumes, réseaux et secrets requises avant toute exécution distante. Production interdite ; aucune capacité distante déclarée acquise.
- Aucun faux succès : report, skips et résultats partiels ne valent pas validation. Tests applicables réussis, QA indépendante positive et absence de blocages restent nécessaires avant fusion. F02 attend F01 fusionnée et conserve le build/démarrage local reproductibles.
- PostgreSQL réel obligatoire avec schémas isolés, sans substitution SQLite ; manque de preuve DB bloquant pour F01. Compose reste sans objet à F01.
- État F01 cohérent avec les éléments transmis : correctif JSON `6d3cd45`, QA `7d49b65`, 51 tests réussis, 2 erreurs DB ; blocages DB et PyAV absent non levés (suivi : PyAV lié au disque). F01 non validée, fusion bloquée. A01 fusionnée en `9ae4a0d` ; ancien suivi explicitement historique.
- Ces résultats applicatifs sont transmis, non reproduits ici. La mention de 0 skip et la mesure disque restent attribuées au suivi auteur. Aucun audit de code, test applicatif, accès endpoint ou déploiement effectué ; tests applicatifs sans objet pour cette revue.

## Commandes et preuves

Commandes exécutées à la racine du worktree. Après rejet initial Git « dubious ownership », utilisation de cette fonction temporaire PowerShell, sans modifier la configuration Git globale :

```powershell
function git { & git.exe -c safe.directory=E:/Dev/nianzeuhub-main/nianzeuhub-main/worktrees/qa-test-strategy @args }
Get-Content -Encoding UTF8 AGENTS.md
git status --short
git branch --show-current
git rev-parse HEAD
git diff 9ae4a0d ba8b0d05323ee491bddb35b1fe1ca6b79d3d09fd -- plan.md docs/contracts/verification.md docs/progress.md
git diff --check 9ae4a0d ba8b0d05323ee491bddb35b1fe1ca6b79d3d09fd
git show ba8b0d05323ee491bddb35b1fe1ca6b79d3d09fd:plan.md
git show ba8b0d05323ee491bddb35b1fe1ca6b79d3d09fd:docs/contracts/verification.md
git show ba8b0d05323ee491bddb35b1fe1ca6b79d3d09fd:docs/progress.md
git diff --name-only 9ae4a0d ba8b0d05323ee491bddb35b1fe1ca6b79d3d09fd
```

Lectures et contrôles réussis ; `git diff --check` : code 0, aucune sortie. Liste des changements : exactement les trois documents attendus. Aucun défaut bloquant identifié dans cette modification documentaire ; ce verdict ne valide ni F01 ni un environnement de test.
