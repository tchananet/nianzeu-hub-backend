# Q01 — revue de sécurité

Suite : `tests/security/`. Rédigée après X01, indépendamment des suites de module, pour
vérifier des propriétés transversales qu'aucun module ne peut prouver seul.

## Ce qui est prouvé et exécuté

52 tests passent sans base de données. Commandes réellement exécutées, à la racine du dépôt :

```
python -m ruff check .      # code 0, « All checks passed! »
python -m mypy app          # code 0, 104 fichiers
python -m pytest -q tests/security   # 52 réussis, 5 bloqués (voir plus bas)
```

### Ordre des contrôles (`test_control_order.py`)

L'application assemblée reçoit une base qui refuse **toute** connexion. Un 503 signifierait
donc que la requête a atteint le compteur de quota. Obtenir 403 ou 415 à la place prouve
positivement que les contrôles de transport et d'origine passent avant tout accès base,
comme l'exige l'ordre de `docs/contracts/http.md`. Vérifié sur sept routes mutantes :
absence d'`Origin`, origine étrangère, `Sec-Fetch-Site: cross-site`, en-têtes `Origin`
dupliqués, absence d'intention `X-Auth-Intent` sur les routes de créancialité, et
`Content-Type` de formulaire refusé en 415 — exactement la forme qu'emprunterait une page
tierce pour poster des identifiants.

### Clés de quota (`test_quota_keys.py`)

Aucune adresse ni aucun email en clair : empreinte HMAC de 64 hexadécimaux, dépendante du
secret serveur, donc non réversible par force brute sur les seules adresses. Deux
propriétés anti-contournement sont vérifiées : `::ffff:198.51.100.23` et `198.51.100.23`
partagent une clé, et deux écritures équivalentes d'une adresse IPv6 aussi. Sans cela, un
client doublerait chaque limite par IP en changeant de représentation.

### Réinitialisation et cookies (`test_reset_and_cookies.py`)

`unavailable_reset()` lève `EMAIL_UNAVAILABLE` en 503 : échec explicite, jamais une fausse
réussite, et aucune recherche de compte même pour un email inconnu. Cookie `__Host-session`
en mode sûr, nom distinct en local non chiffré, `SameSite=Lax` par défaut et `None`
uniquement lorsque le cross-site est déclaré avec HTTPS.

### Absence de fuite (`test_no_information_leak.py`)

Sur sept sondes, le corps d'erreur ne contient ni l'instruction SQL, ni le message du
pilote, ni le nom d'une table, ni une trace d'exécution, ni l'URL de base de données, ni le
secret de quota, ni les clés de stockage. L'enveloppe est exactement
`{error:{code,message,details}, request_id}`, `details` toujours un tableau vide hors
validation, `X-Request-ID` présent partout y compris sur la santé, et `Cache-Control:
no-store` sur les lectures privées.

## Ce qui reste bloqué

`tests/security/test_cross_session.py` : 5 tests **écrits et non exécutés**. Ils exigent
`SECURITY_TEST_DATABASE_URL` vers un PostgreSQL réel en loopback avec les migrations
appliquées ; sans elle ils échouent en blocage explicite. SQLite n'est jamais substitué et
aucun de ces tests n'est compté comme réussi.

Ils couvrent la preuve transversale de `http.md` : un intrus reçoit 404 sur l'élément d'un
tiers en lecture, suppression, publication et dépublication, et l'élément du propriétaire
est toujours présent ensuite ; une session valide sans jeton CSRF reçoit 403 ; une session
révoquée reçoit 401 ; un identifiant de propriétaire envoyé par le client est refusé en
422 ; une coordonnée marquée privée n'apparaît ni sur le profil public ni sur les contacts
publics.

La variable est désormais fournie par `ops/test-portainer/compose.suite.yaml`, donc ces cinq
tests s'exécuteront à la prochaine campagne distante. **Tant que cette campagne n'a pas
produit de résultat, Q01 n'est pas validée.**

## Verdict

**Partiel.** Les propriétés vérifiables sans base le sont et passent. Les propriétés
transversales nécessitant une base sont écrites mais non éprouvées. Aucun blocage de
sécurité n'a été découvert dans le périmètre exécuté ; aucune conclusion ne peut être tirée
du périmètre non exécuté.
