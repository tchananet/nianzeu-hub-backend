# HTTP v1 — règles communes (décisions A01)

Préfixe `/api/v1`. JSON UTF-8 ; corps maximum 64 KiB (413 `BODY_TOO_LARGE`), sauf transfert fichier direct MinIO. Content-Type JSON exigé pour corps JSON (415 `UNSUPPORTED_MEDIA_TYPE`). Toutes les entrées sont validées strictement : champs inconnus rejetés, pas de coercition booléen/nombre/chaîne. Corps malformé 400 `INVALID_JSON`, champ invalide 422 `VALIDATION_ERROR`. Paramètres query numériques sont des chaînes décimales converties puis bornées ; query inconnue ou répétée rejetée 422, sauf `skill_id` explicitement multivalué. Identifiants UUID, dates ISO `YYYY-MM-DD`, instants UTC RFC3339 terminés par `Z`. Chaînes trimées sauf mot de passe ; rejeter caractères de contrôle, HTML traité comme texte, jamais exécuté. Pas d'URL arbitraire récupérée par le serveur.

Succès : objet JSON décrit par route ; collections `{"items":[],"page":1,"page_size":20,"total":0}`. Pagination offset : page 1..500, page_size 1..50 défaut 20, offset maximum 10 000 (sinon 422), total calculé sur les mêmes filtres. Tri stable avec UUID comme dernier critère ; pas de garantie snapshot entre deux pages concurrentes.

Erreur unique : `{"error":{"code":"VALIDATION_ERROR","message":"Invalid request","details":[{"field":"body.email","code":"invalid"}]},"request_id":"uuid"}`. `details` est toujours un tableau, vide hors validation ; aucun input, SQL, secret ni stack trace inclus. `X-Request-ID` généré côté serveur UUID retourné pour tous les statuts, même health. Les clients utilisent `code`, pas le texte localisable.

| HTTP | Codes et conditions |
|---|---|
| 400 | INVALID_JSON, INVALID_UPLOAD (octets corrompus/incompatibles) |
| 401 | AUTH_REQUIRED (cookie absent, expiré, révoqué, utilisateur inactif), INVALID_CREDENTIALS (login uniforme) |
| 403 | CSRF_FAILED, ORIGIN_FORBIDDEN ; aucune différence d'ownership révélée |
| 404 | NOT_FOUND (ressource absente, privée, appartenant à autrui, profil supprimé) |
| 409 | EMAIL_UNAVAILABLE, PROFILE_REQUIRED, INVALID_STATE, QUOTA_EXCEEDED, UPLOAD_EXPIRED |
| 413 | BODY_TOO_LARGE, FILE_TOO_LARGE |
| 415 | UNSUPPORTED_MEDIA_TYPE |
| 422 | VALIDATION_ERROR |
| 429 | RATE_LIMITED ; `Retry-After` entier secondes jusqu'au prochain créneau |
| 503 | EMAIL_UNAVAILABLE, DEPENDENCY_UNAVAILABLE, VALIDATION_BUSY, SCHEMA_NOT_READY |
| 500 | INTERNAL_ERROR (journalisé, aucune exception absorbée) |

Ordre de contrôle : limite transport → Origin sur mutations → quota IP → session si requise → CSRF → validation des champs → existence/ownership → quota métier/transition → transaction. Login a quota par identifiant après parsing. Les 404 d'ownership se testent avec une session et un CSRF valides. Pas de 405/404 framework non enveloppé ; adapter handlers HTTP et validation. Méthode inconnue : 405 `METHOD_NOT_ALLOWED` avec Allow ; route inconnue 404.

Routes privées et fichiers : `Cache-Control: no-store`, `Vary: Origin`. Profils/recherche/contacts publics : également no-store au MVP pour retrait immédiat des coordonnées ; aucun cache CDN. Préflight OPTIONS 204 pour origine autorisée, méthodes/headers déclarés seulement ; jamais une mutation.

## Quotas de requêtes

Fenêtres fixes UTC, incrément atomique PostgreSQL `INSERT ... ON CONFLICT ... UPDATE ... RETURNING` ; la requête N+1 est refusée, échecs inclus. Clés IP via HMAC du client normalisé et secret serveur ; identifiant login via HMAC de l'email normalisé. Pas d'email/IP brut en table quotas. Suppression des fenêtres expirées après 24 h ; stockage indisponible → 503, pas de bypass. Les fenêtres concurrentes ne dépassent jamais N par clé ; le double débit à cheval sur deux fenêtres est accepté/documenté.

| Groupe | Limite |
|---|---|
| register | 5 / heure / IP |
| login | 30 / 15 min / IP **et** 10 / 15 min / email normalisé |
| forgot/reset | 5 / heure / IP, même lorsque désactivés |
| lectures publiques JSON | 120 / minute / IP, groupe partagé |
| lectures privées | 120 / minute / utilisateur |
| mutations authentifiées | 60 / minute / utilisateur, groupe partagé |
| upload-url et validate | chacun 10 / heure / utilisateur, en plus du groupe mutations |
| vues | 30 / minute / IP ; une vue / profil / IP-HMAC / jour |
| contenu fichier | 60 / minute / IP, streaming borné par architecture |

Health est interne au proxy et exempt de quotas DB pour ne pas créer de dépendance circulaire. GET CSRF utilise le quota lectures privées. Les quotas ne constituent pas une capacité VPS démontrée.

## Exemple de preuve transversale

Avec deux sessions A/B : chaque route `/me` ignore tout identifiant propriétaire envoyé par client (champ inconnu 422). Toute mutation sur item B par A retourne 404 sans effet DB/MinIO. Session valide sans CSRF retourne 403 sans effet. Une requête après révocation retourne 401. Quota N atteint, N+1 retourne 429 avec Retry-After ; deux workers partagent le même compteur.
