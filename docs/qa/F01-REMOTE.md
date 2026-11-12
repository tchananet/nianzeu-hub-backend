# QA F01-REMOTE — VALIDÉ

Date : 2026-11-12. QA indépendante, branche `test/qa-f01-remote`, base `86822068afe71d7a0116d2267c13785a6b64c1d2`.
Ownership : ce rapport et `docs/qa/F01.md`. Aucune installation locale, aucun code modifié.
Candidat original : `6d3cd45cb4f9b7685cbda06bf4ecaf9207d44c05`.
Harness revu : `a75fcfc1f88a3d3b1d8fafc6d1d09b2204d7cdd5`.
Candidat intégré revu et reproduit : `f7859b2ce47c57cf5a013828fcbb48c7914edf34`.
Verdict : F01 validé à ces SHA ; aucune validation F02/M01 ni fusion effectuée par QA.

## Revue et provenance

AGENTS, plan et rapport R2 `7d49b65:docs/qa/F01.md` lus. CODE-01 résolu ; ENV-01/ENV-02 alors ouverts.
Commandes Git avec `-c safe.directory=<worktree>` ; aucune configuration globale modifiée.
`git diff 6d3cd45 f7859b2 -- app tests pyproject.toml uv.lock` : vide, code 0.
`git diff a75fcfc f7859b2 -- ops/test-portainer` : vide, code 0.
Diff documentaire intégré lu ; aucune modification applicative ou résolution de conflit de code.
`git diff --check 6d3cd45 f7859b2` et `git diff --check a75fcfc^ a75fcfc` : code 0.
Harness : Compose 77 lignes, helper 6 ; syntaxe vérifiée selon auteur, non reproduite localement par QA.
Compose intégré : exactement trois remplacements du SHA complet original (fetch, assertion, marqueur).
`StackFileInspect(103)` égale exactement la chaîne envoyée ; contenu 102 également relu.
SHA256 Compose UTF-8/LF original : `9e2f5c8dfc45ff4e8f459af0233d0e840379cfbbc3d767b3774d0aecc58bc0da`.
SHA256 Compose UTF-8/LF intégré : `1b1a37fa9211a2ccd31ffb3a857f01e07b9e931cca9bcf57f4bbf8337eec1ccc`.

## Exécution indépendante et isolation

Endpoint 3 identifié directement via MCP : `diddifree-prod`, Docker standalone.
Avant chaque création : StackList et GET /containers/json (all=true, filtre nom), /volumes, /networks : aucune collision du préfixe QA.
QA appelle `StackCreateDockerStandaloneString(endpointId=3, Name=..., StackFileContent=...)` ; aucun shell hôte.
Stack 102 : `nianzeu-f01-qa-6d3cd45`, volume neuf `nianzeu-f01-qa-6d3cd45_work`.
Runner 102 : `3989650596d592b2e11a5eca59557440d6196ac20ba3f989afb6fd3c07e0d2c1` ; DB : `61c193bcdab119446dc313343ec4d37aef57cdcff4021a4a89897a7b7e88c4b2`.
Stack 103 : `nianzeu-f01-qa-f7859b2`, volume neuf `nianzeu-f01-qa-f7859b2_work`.
Runner 103 : `9e83961d812cfc6f601a195cd4cac912c93e4fc82d7d1167ab732205aae02e7c` ; DB : `da2d6591315c628f2d74720040866c6ecabaea27d536e7db3d723c47cd593c71`.
GET /containers/{id}/json confirme runner 1 CPU/2147483648 octets/256 PID ; DB 0.5 CPU/536870912 octets/128 PID.
Services non privilégiés, PortBindings {}, logs json-file max-size=5m/max-file=2 ; aucun montage hôte/socket.
Runner : seul volume work neuf, réseau container:{sa DB}. DB : réseau du projet, tmpfs données 268435456 octets.
PostgreSQL 16.15 confirmé par logs, écoute 127.0.0.1:5432. Script revu : rôle f01 NOSUPERUSER/NOCREATEDB/NOCREATEROLE, DB f01_test ; création observée dans les logs 102, sans interrogation directe des attributs SQL.
Timeout runner 900 s puis kill après 10 s ; pulls hors timeout. DB arrêtée explicitement après runner.
Images inspectées via GET /images/{id}/json, mêmes digests pour les deux runs :
- `python@sha256:cc55e4ded9c95f6ce2133b3d096db43f214d280c2a8af65d83e246c8fa7d168c`.
- `postgres@sha256:0cefaabd882e42bcb2a2f3dc56d3ce4770560ba62fd7f197f1a2e008fd5731ab`.

## Commandes et résultats

Dans /work/source : Python 3.13.18, uv 0.11.6, Ruff 0.17.4, Mypy 1.20.2, pytest 9.2.0, PyAV 17.1.0.
Fetch HTTPS public du SHA exact, checkout détaché et assertion HEAD avant installation, aucun token.
Chaque commande ci-dessous réussit dans 102 ET 103 : code 0 déduit de bash -euo pipefail, séquence complète et sortie finale 0 ; les codes individuels ne sont pas imprimés.

| Commande exacte | Résultat |
|---|---|
| `python -m pip install --no-cache-dir uv==0.11.6` | installé |
| `uv sync --locked --python 3.13 --all-groups --all-extras` | 49 paquets installés, PyAV inclus |
| `uv sync --locked --check --python 3.13 --all-groups --all-extras` | Checked 49 packages ; Would make no changes |
| `uv run --no-sync python -c 'import av; print("PyAV", av.__version__)'` | PyAV 17.1.0 |
| `uv run --no-sync ruff check .` | All checks passed |
| `uv run --no-sync mypy app` | Success, 14 source files |
| `uv run --no-sync pytest tests/core` | 102 : 53 passed/2.92 s ; 103 : 53 passed/4.77 s |
| `uv run --no-sync pytest` | 102 : 53 passed/2.30 s ; 103 : 53 passed/2.47 s |
| `git diff --exit-code -- pyproject.toml uv.lock` | aucun changement |

Chaque suite : 53 collectés, zéro skip, deux tests PostgreSQL réussis, six tests JSON inclus (pas de double comptage).
Avertissement Starlette/httpx déprécié unique par suite ; pip root, fallback copie uv et locale Alpine observés, non bloquants.
Runner 102 : 12:27:58.234997379 → 12:28:37.057442555 UTC ; exited, ExitCode=0, OOMKilled=false.
Runner 103 : 12:29:34.553465954 → 12:30:09.824386261 UTC ; exited, ExitCode=0, OOMKilled=false.
Marqueurs F01_REMOTE_PASS avec SHA exact présents après contrôles ; verdict fondé aussi sur compteurs et inspect.
Préflight 102 : /work libre 203207225344 octets ; MemAvailable 39616536576 octets.
Préflight 103 : /work libre 202800758784 octets ; MemAvailable 39603384320 octets (indices, non réservations).
`git archive --format=tar HEAD | sha256sum` : original `e0e4a7ca6a3459ce1042ce1a90353aa2adc2fdf163f3f6c96754dc34c3c6c81a` ; intégré `ddeaa59c165edd52d8f20a8e5c9a5c7629d30baebfebeba3b5d4ff4e6520d285`.
`sha256sum uv.lock` identique : `5286bb86a00eb5317a739198bd349a6fbaa4d02bf58c72b8c2aafae2ab9a2f23`.

## Collecte, arrêt et portée

Lectures QA : GET /containers/{id}/logs avec stdout=true, stderr=true, timestamps=true, tail=180 (runner), 70/15 (DB), sans follow ; GET /containers/{id}/json et /images/{id}/json avec projections.
Après sorties constatées, POST /containers/{postgres-id}/stop?t=10 uniquement pour DB QA 102/103 ; inspections ultérieures : exited/running=false/ExitCode=0.
DB 103 arrêtée à 12:30:28.460699246 UTC. Aucune suppression : stacks/volumes QA conservés pour inspection ; aucun service/domaine préexistant modifié.
Run auteur 101 : initialement transmis par parent, puis logs et inspect runner relus directement par QA (0, aucun OOM, 53 passed en 2.95/2.25 s). Arrêt DB déclaré par parent ; QA ne l'a pas modifiée.
Résultat indépendant fondé sur 102 et surtout 103, pas sur la déclaration auteur.
ENV-01/ENV-02 levés au candidat intégré exact ; CODE-01 reste résolu. Main non modifié par QA.
Toute évolution applicative/contractuelle ultérieure exige revue et contrôles adaptés ; produits F02/M01 hors verdict.
Écriture initiale interrompue par disque plein, reprise après nettoyage de caches/venvs par le parent ; aucune dépendance locale utilisée.
