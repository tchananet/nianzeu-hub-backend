# Reprise de session

`main` = `122cdc4`, poussé sur `origin`. Tout est committé et poussé.

## État

Toutes les missions du plan sont fusionnées sauf Q02. `ruff` et `mypy` passent
(104 fichiers source), **460 tests passent** en local, aucun fichier manuel ne dépasse
100 lignes, tête Alembic unique `0003_portfolio_search`.

| Mission | État |
|---|---|
| A01, F01, F02, M01, I01, M02, P01, M03, R01 | fusionnées et vérifiées |
| O01 portfolio | fusionnée ; couverture au niveau route encore incomplète |
| X01 assemblage | fusionnée ; 24 routes prouvées montées |
| B01 sauvegarde | fusionnée ; outillage **jamais éprouvé** faute de Docker |
| D01 runbook | fusionnée |
| Q01 sécurité | partielle ; 52 preuves exécutées, 5 en attente de PostgreSQL |
| Q02 charge | non commencée, bloquée |

## Blocage principal : campagne sur PostgreSQL réel

**246 tests sont écrits et non exécutés** faute de base accessible. Ils ne sont jamais
comptés comme réussis et SQLite n'est jamais substitué.

Le serveur MCP Portainer s'est déconnecté pendant cette session et n'est pas revenu, donc
la campagne distante n'a pas pu être relancée. Pour la relancer :

1. Reconnecter le serveur MCP Portainer.
2. Redéployer la stack de test **105** (`nianzeu-m01-author-34b22f5`, environnement 3) avec
   `ops/test-portainer/compose.suite.yaml`, qui fournit désormais les cinq variables
   attendues : `TEST_DATABASE_URL`, `IDENTITY_TEST_DATABASE_URL`,
   `PROFILES_TEST_DATABASE_URL`, `DISCOVERY_TEST_DATABASE_URL` et
   `SECURITY_TEST_DATABASE_URL`.
3. Lire les journaux du conteneur `…-runner-1`. Il résout `origin/main`, journalise le
   commit testé, applique les migrations puis exécute `ruff`, `mypy` et `pytest`.

Dernière campagne réussie, au commit `38a177f` : **411 réussis, 2 ignorés, 2 échecs**. Les
deux échecs étaient des assertions `NOT NULL` inatteignables dans les aides de test de M03,
corrigées depuis. Base en tmpfs, aucune écoute publiée, aucun volume hôte ; aucune stack de
production n'est touchée.

## Reste à faire

1. **Campagne distante** ci-dessus : seule preuve acceptable pour les 246 tests.
2. **O01, couverture au niveau route** : la liste précise est dans `docs/missions/O01.md`
   (MIME forgé, sha256 faux, taille excessive, écrasement de quarantaine, concurrence de
   quota, panne de stockage et bail expiré, retrait public après dépublication).
3. **B01, répétition réelle** : sauvegarde → restauration → vérification sur un hôte muni
   de Docker. `docs/backup.md` et `docs/missions/B01.md` décrivent la procédure ; GAP-12
   reste ouvert tant qu'elle n'a pas tourné.
4. **Q02 charge** : bloquée faute de VPS de test autorisé. A01 fixe les seuils.
5. **GAP-01 et GAP-11** de `docs/deployment-gaps.md` : accès de Nginx Proxy Manager à une
   publication loopback, et absence de `migrations/` dans l'image livrée.

## Environnement local

Environnement Python isolé **hors du dépôt**, car `E:` est presque plein :

```bash
export UV_PROJECT_ENVIRONMENT="C:/Users/Vanauld/AppData/Local/Temp/claude/nianzeu-venv"
export UV_LINK_MODE=copy
cd E:/Dev/nianzeuhub-main/nianzeuhub-main/backend
uv run ruff check . && uv run mypy app && uv run pytest -q
```

Ni Docker local, ni PostgreSQL local, ni Supabase. Les sous-agents utilisaient
`…/nianzeu-venv/Scripts/python.exe -m pytest` directement pour éviter les accès
concurrents à `uv`.
