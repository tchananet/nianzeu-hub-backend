# Reprise de session — 2026-11-12

`main` = `e3a3a24`, poussé sur `origin`. Tout le travail décrit ici est committé et poussé,
sauf mention explicite du contraire.

## Ce qui est fusionné dans `main`

A01, F01, F02, M01, I01, M02, P01, M03, R01, et l'assemblage X01 partiel.
`ruff` et `mypy` passent ; 288 tests passent en local, 411 sur PostgreSQL réel.
Tête Alembic unique : `0003_portfolio_search`.

## État par mission

| Mission | Branche | État |
|---|---|---|
| M03 migration portfolio et index | `feat/m03-portfolio-search` | fusionnée |
| R01 recherche publique | `feat/r01-discovery` | fusionnée |
| D01 runbook de déploiement | `docs/d01-deployment` | **livrée, non fusionnée** (8 docs) |
| O01 portfolio | `feat/o01-portfolio` | **3 commits poussés, agent interrompu** |
| B01 sauvegarde | `feat/b01-backup` | **aucun commit : à relancer entièrement** |
| X01 assemblage | `main` | identité, profils, contact, recherche montés ; **portfolio à monter** |
| Q01 sécurité indépendante | — | à faire, dépend de X01 complet |
| Q02 charge | — | bloquée : aucun VPS de test autorisé |

## À faire à la reprise, dans cet ordre

1. Vérifier O01 : `git log main..feat/o01-portfolio`, relire les trois commits, lancer
   `ruff`, `mypy`, `pytest` dans un worktree, puis fusionner. L'agent n'a pas rendu de
   rapport : considérer la mission comme non revue et vérifier qu'aucune migration n'a
   été créée et qu'aucun fichier manuel ne dépasse 100 lignes.
2. Compléter X01 : ajouter le routeur portfolio dans `app/wiring.py`. Le client MinIO est
   déjà construit dans `create_app` et exposé par `application.state.storage`.
3. Fusionner D01 après relecture.
4. Relancer B01 (sauvegarde PostgreSQL + MinIO cohérente, restauration prouvée).
5. Écrire Q01 (`tests/security/`, `docs/qa/security.md`).

## Environnement de vérification

Environnement Python isolé, **hors du dépôt** car `E:` est presque plein :

```bash
export UV_PROJECT_ENVIRONMENT="C:/Users/Vanauld/AppData/Local/Temp/claude/nianzeu-venv"
export UV_LINK_MODE=copy
cd E:/Dev/nianzeuhub-main/nianzeuhub-main/backend
uv run ruff check . && uv run mypy app && uv run pytest -q
```

Les agents utilisaient directement `…/nianzeu-venv/Scripts/python.exe -m pytest` pour
éviter les accès concurrents à `uv`. Ni Docker local, ni PostgreSQL local, ni Supabase.

Preuve sur PostgreSQL réel : stack Portainer de test **105** (`nianzeu-m01-author-34b22f5`),
environnement 3. Fichier déployé : `ops/test-portainer/compose.suite.yaml`. Le runner résout
`origin/main`, journalise le commit testé, applique les migrations puis exécute
`ruff`, `mypy` et `pytest`. Pour relancer : redémarrer le conteneur `…-runner-1` puis lire
ses journaux. Base en tmpfs, aucune écoute publiée, aucun volume hôte, aucune stack de
production touchée.

**Variables manquantes dans le harnais** : il fournit `TEST_DATABASE_URL`,
`IDENTITY_TEST_DATABASE_URL` et `PROFILES_TEST_DATABASE_URL`. R01 attend
`DISCOVERY_TEST_DATABASE_URL` et O01 aura probablement sa propre variable ; il faut les
ajouter au `compose.suite.yaml` avant la prochaine exécution complète, sinon ces tests
échouent en blocage explicite et non en réussite.

## Défauts à traiter, signalés par D01

- **GAP-02, sérieux** : le `Dockerfile` lance uvicorn avec `--no-proxy-headers`, donc
  `request.client.host` est l'adresse du proxy. Tous les quotas par IP partagent alors un
  seul compteur et la déduplication des vues de profil fusionne tous les visiteurs. Correctif
  prévu : retirer `--no-proxy-headers` et fixer `FORWARDED_ALLOW_IPS` à l'adresse du proxy.
  **Non corrigé à cette heure.**
- **GAP-01** : Nginx Proxy Manager sur un réseau bridge ne peut pas joindre une publication
  sur `127.0.0.1`.
- **GAP-11** : l'image ne contient ni `alembic.ini` ni `migrations/`, donc les migrations ne
  peuvent pas être appliquées depuis l'image livrée.
- Registre complet : `docs/deployment-gaps.md` sur la branche D01.
