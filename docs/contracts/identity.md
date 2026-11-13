# Identité et sessions v1 (décisions A01)

## Routes

Les routes sont sous `/api/v1`. `User` public à son propriétaire : `{id:uuid,email:string,role:"talent",created_at:instant}` ; jamais hash, sessions ni compteur quotas. Aucun paramètre role accepté à l'inscription.

| Méthode / route | Entrée | Succès | Accès / erreurs spécifiques |
|---|---|---|---|
| POST `/auth/register` | `{email,password}` requis | 201 `{user:User}` ; pas de session automatique | anonyme, Origin requis ; 409 EMAIL_UNAVAILABLE doublon |
| POST `/auth/login` | `{email,password}` requis | 200 `{user:User,csrf_token:string}` + cookie session neuf | anonyme, Origin requis ; 401 INVALID_CREDENTIALS identique email absent/mauvais secret/inactif |
| POST `/auth/logout` | aucun corps | 204 sans corps, cookie expiré | session+CSRF ; 401 si déjà invalide |
| GET `/auth/me` | aucune | 200 `{user:User}` | session |
| GET `/auth/csrf` | aucune | 200 `{csrf_token:string}` | session, no-store ; accès navigateur même origine uniquement |
| POST `/auth/password/forgot` | `{email}` | aucun succès tant que désactivé | Origin, quota ; 503 EMAIL_UNAVAILABLE après validation |
| POST `/auth/password/reset` | `{token,password}` | aucun succès tant que désactivé | Origin, quota ; 503 EMAIL_UNAVAILABLE après validation |

Email : longueur 3..254, validation syntaxique sans appel DNS ; trim, conversion ASCII lowercase de l'adresse entière ; domaine IDNA en ASCII, local-part ASCII uniquement. La normalisation est identique login/register/SQL. Mot de passe : 12..128 caractères Unicode, maximum 512 octets UTF-8, pas de trim/normalisation silencieuse, aucun critère arbitraire de classes. Token reset : chaîne base64url 43..128 caractères syntaxiques, aucun token émis au MVP. Deux requêtes forgot avec emails existant/inexistant valides reçoivent exactement le même 503 sans recherche de compte, création de token ou appel fournisseur. Corps invalide reste 422 ; quota dépassé 429.

Argon2id : mémoire 64 MiB, itérations 3, parallélisme 1, sel aléatoire 16 octets minimum, hash 32 octets ; paramètres enregistrés dans le hash encodé. Comparaison par bibliothèque maintenue ; hash factice pour email absent afin de limiter les différences temporelles. Réhash au login si paramètres obsolètes. F01 verrouille les dépendances, I01 mesure les coûts ; pas de promesse de latence sans QA.

## Session opaque

Secret aléatoire cryptographique 32 octets, encodage base64url sans padding ; seul SHA-256 du secret stocké en DB. ID de session distinct UUID. Cookie production : `__Host-session=<secret>; Path=/; Secure; HttpOnly; SameSite=Lax`, aucun Domain, Max-Age 604800 (7 jours). Expiration absolue 7 jours et inactivité 24 h, appliquées côté serveur à chaque requête protégée. `last_seen_at` actualisé atomiquement après contrôle ; ne dépasse jamais expiration absolue. Logout révoque immédiatement la ligne et expire cookie avec mêmes attributs. Cookie local HTTP : `session_local`, seulement environnement local/test explicite.

Chaque login génère un nouveau secret et un CSRF indépendant de 32 octets. Ancienne session fournie au login révoquée si valide ; aucune fixation de session. Maximum 5 sessions actives par utilisateur ; à la sixième, révocation de la plus ancienne (created_at,id), sous verrou utilisateur. Deux connexions concurrentes respectent ce plafond. Utilisateur inactif invalide toutes les authentifications. Aucun endpoint de changement mot de passe/rôle ni de liste sessions dans ce MVP.

CSRF : jeton synchronisé propre à la session, secret conservé côté serveur dans la session (accès DB restreint, jamais logs). Toutes les mutations authentifiées exigent `X-CSRF-Token` égal au secret en comparaison temps constant, y compris logout/upload/publication/suppression. GET `/auth/csrf` permet de le récupérer après rechargement ; aucune mutation via GET. Les origines acceptées forment une liste close tenue dans `app/core/origins.py` : `https://diddifree.com`, `https://netatroniks.xyz` et tout sous-domaine `*.diddifree.com`, en HTTPS sur le port 443 uniquement ; en environnement `local` ou `test`, `http://localhost` est également admis. **Décision assumée** (revue `docs/qa/I01.md`, défaut I01-01) : un sous-domaine `*.diddifree.com` est donc une origine de confiance. La protection CSRF ne repose pas sur l'origine seule — le jeton synchronisé reste exigé sur chaque mutation — mais un sous-domaine compromis franchit le contrôle d'origine. `APP_FRONTEND_ORIGIN` est validé au démarrage et n'est consulté par aucun contrôle à ce jour : il est réservé à la future politique CORS (GAP-03) et ne restreint pas l'origine acceptée.  Origin absent ou `null` refusé 403 sur toutes les mutations, y compris login/register/reset et vues anonymes. Les clients non navigateurs fournissent explicitement Origin. Si `Sec-Fetch-Site` présent, `cross-site` refusé ; ce contrôle complète, sans remplacer, Origin et jeton. Pas de token pré-session requis pour login/register : Origin strict protège ces routes, aucune action sur une session existante sauf rotation au login.

## Acceptation I01

Inscription 201 puis doublon normalisé 409, concurrence doublon → une seule ligne ; login correct 200, erreurs uniformes 401 ; cookie et expiration vérifiés avec horloge injectée ; CSRF absent/faux et Origin absent/hostile 403 ; logout 204 puis me 401 ; sessions expirées/révoquées 401 ; six logins → cinq sessions actives ; comptes A/B isolés ; forgot/reset 503 uniformes, EmailPort désactivé lève explicitement et aucune table reset alimentée. Vérifier absence de secrets dans logs/JSON et race limite login dans deux connexions DB.
