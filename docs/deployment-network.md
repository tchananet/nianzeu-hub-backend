# Déploiement — TLS, proxy, CORS et sessions

Annexe de [deployment.md](deployment.md). Décrit le comportement du code au SHA `6e827ff`.

## Terminaison TLS et en-têtes de proxy

NPM termine TLS ; l'API sert du HTTP clair sur 8000. Le `Dockerfile` lance
`uvicorn … --workers 2 --no-proxy-headers --no-access-log` : l'application **ignore
totalement** `X-Forwarded-Proto`, `X-Forwarded-For` et `X-Forwarded-Host`. Conséquences :

- L'attribut `Secure` du cookie vient uniquement de `APP_SECURE_COOKIES`, jamais du proxy :
  il doit rester `true` en production, et la configuration refuse le contraire
  (« Secure cookies required outside local/test »).
- Le cookie s'appelle `__Host-session` quand `secure` est vrai
  (`app/modules/identity/browser.py`) : le navigateur doit voir HTTPS, `Path=/`, aucun
  `Domain`, `HttpOnly`, `Max-Age=604800`. La terminaison TLS au proxy est donc obligatoire.
- `request.client.host` est l'adresse du pair, donc celle du proxy. Toutes les clés de quota
  par IP (`ip_quota_key` dans `app/core/primitives.py`, utilisé par
  `app/modules/identity/limits.py` et `app/modules/profiles/access.py`) se réduisent à une
  seule clé partagée par tous les visiteurs — voir GAP-02, à traiter avant exposition publique.

Côté NPM : transmettre `Host`, forcer la redirection HTTPS, et aligner la taille de corps
acceptée sur le contrat HTTP (JSON borné à 64 KiB). Les transferts de fichiers du portfolio
vont directement à MinIO par formulaire POST présigné, jamais à travers l'API.

Le service `api` étant publié sur `127.0.0.1` seulement, la terminaison TLS est le **seul**
chemin d'entrée prévu. Aucun autre reverse proxy ne doit publier 8000 ou 9000 publiquement.

## Origine frontend et CORS

`APP_FRONTEND_ORIGIN` doit passer l'allowlist codée dans `app/core/origins.py`
(`is_allowed_origin`) :

| Environnement | Origines acceptées |
|---|---|
| `production` | `https://diddifree.com`, `https://netatroniks.xyz`, tout `*.diddifree.com`, port 443 uniquement |
| `local`, `test` | les précédentes **plus** `http://localhost[:port]` |

L'origine est normalisée (port par défaut retiré, aucun chemin, aucun userinfo, labels DNS
valides). Toute autre valeur fait échouer le démarrage avec « Origin is not allowed ».

La décision A01-02 est **même origine** : frontend et `/api` derrière un seul nom HTTPS.
Aucun middleware CORS n'est installé dans `app/main.py` ; les constantes `CORS_METHODS`,
`CORS_HEADERS` et `CORS_EXPOSE_HEADERS` d'`origins.py` sont déclarées mais inutilisées, et le
préflight `OPTIONS 204` décrit dans `contracts/http.md` n'existe pas. Servir le frontend sur
une origine différente de l'API échouerait donc côté navigateur — voir GAP-03.

Ce qui est réellement appliqué aujourd'hui (`BrowserPolicy` dans
`app/modules/identity/browser.py`) :

- `Origin` est **exigé** sur toute mutation, y compris `login`, `register` et les routes de
  reset ; absent, multiple ou hors allowlist → 403 `ORIGIN_FORBIDDEN`.
- `Sec-Fetch-Site: cross-site` est refusé tant que les sessions cross-site sont désactivées.
- Les lectures authentifiées exigent `Origin` seulement quand le mode cross-site est actif ;
  `GET /auth/csrf` l'exige toujours.
- Les réponses privées portent `Cache-Control: no-store` et `Vary: Origin`
  (`app/modules/identity/routes.py`, `private_routes.py`, `app/modules/profiles/access.py`,
  `app/shared/http_errors.py`). Les lectures publiques sont également `no-store` au MVP :
  **ne pas placer de cache CDN devant l'API.**

## Conditions des sessions cross-site

`APP_SESSION_CROSS_SITE_ENABLED=true` exige simultanément, sous peine de refus de
démarrage (« Cross-site sessions require HTTPS public origin and Secure cookies ») :

1. `APP_SECURE_COOKIES=true` ;
2. `APP_API_PUBLIC_ORIGIN` défini ;
3. cette origine commence par `https://`.

`SameSite` passe alors de `lax` à `none`. Attention : `docker-compose.yml` ne transmet au
service `api` ni `APP_SESSION_CROSS_SITE_ENABLED` ni `APP_API_PUBLIC_ORIGIN` ; les défauts
`false` / `None` s'appliquent et l'activation est **impossible sans modifier le Compose**,
qui n'appartient pas à D01 — voir GAP-04. Le déploiement visé étant à origine unique, ce
mode doit rester désactivé jusqu'à une décision explicite.

Dérogation locale uniquement : `APP_SECURE_COOKIES=false` est accepté seulement si
`APP_ENVIRONMENT` vaut `local` ou `test` **et** `APP_API_PUBLIC_ORIGIN` est exactement un
`http://localhost[:port]` (`is_local_http_api`). Le cookie s'appelle alors `session_local`.
Jamais en production.
