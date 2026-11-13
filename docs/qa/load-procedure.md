# Q02 — mélange de parcours, quotas et procédure d'exécution

Annexe de [load.md](load.md), dont le verdict reste **BLOQUÉ** : rien ici n'a été
exécuté contre une API réelle. Ce document décrit ce que le harnais fait et ce qu'un
exploitant doit lancer pour obtenir de vrais chiffres.

## Mélange de parcours et pourquoi il est réaliste

Mélange imposé par A01 ([contracts/verification.md](../contracts/verification.md)) et
implémenté tel quel dans `tests/load/journeys.py` :

| Part | Parcours | Route |
|---|---|---|
| 50% | recherche anonyme | `GET /api/v1/search/profiles` |
| 25% | profil public | `GET /api/v1/profiles/{id}` |
| 10% | contacts publics | `GET /api/v1/profiles/{id}/contacts` |
| 10% | lecture privée propriétaire | `GET /api/v1/profiles/me` ou `/me/portfolio` |
| 5% | mutation propriétaire | `PUT /api/v1/profiles/me` |

85% de lectures anonymes : le produit est un annuaire public de talents. Un visiteur
cherche, ouvre quelques profils, révèle parfois les coordonnées publiées ; seule la
minorité propriétaire écrit, et rarement. Un mélange plus riche en mutations mesurerait
un usage que ce MVP n'a pas. Le téléversement est volontairement absent du plateau : A01
en fait un scénario distinct (10 utilisateurs, 20 cycles, p95 validation ≤30 s), non
implémenté ici faute de MinIO réel.

Corpus : `tests/load/corpus.py` dérive 500 comptes, profils et contacts de la seule
graine `Q02_SEED` et du `Q02_RUN_ID`. Chaque email porte le préfixe `q02-<run_id>-`,
donc le résidu est identifiable et supprimable ; aucun compte réel n'est touché.

## Quotas : mesurer la capacité, pas son propre refus

Risque principal d'un générateur naïf : tout vient d'une seule IP, l'API répond 429 et
la campagne mesure le limiteur. Les quotas de [contracts/http.md](../contracts/http.md)
sont : lectures publiques 120/min/IP, lectures privées 120/min/utilisateur, mutations
authentifiées 60/min/utilisateur, register 5/heure/IP, login 30/15 min/IP et
10/15 min/email. A01 interdit de les relever pour le test.

Le harnais **mesure la capacité** : il répartit la charge sur 100 sources synthétiques
(`203.0.113.0/24`, TEST-NET-3), une par utilisateur virtuel, portées par l'en-tête
`Q02_SOURCE_HEADER` (défaut `X-Forwarded-For`). Arithmétique au plateau, pensée 1..3 s
(moyenne 2 s) donc ≈0,5 req/s par utilisateur et ≈50 req/s agrégés :

- lectures publiques : 85% × 50 = 42,5 req/s ÷ 100 sources ≈ **25 req/min/source**
  contre 120 autorisées — marge ×4,7 ;
- lectures privées ≈ 3 req/min/utilisateur contre 120 ; mutations ≈ 1,5 contre 60 ;
- amorçage : 500 comptes à 5 inscriptions/heure/IP exigent **exactement** 100 sources,
  sans marge. `seeding.registration_budget()` refuse de démarrer si
  `Q02_ACCOUNTS > Q02_SOURCES × 5`.

Cette répartition n'a d'effet que si le VPS de test est derrière le proxy autorisé et
que uvicorn lui fait confiance (`FORWARDED_ALLOW_IPS`, GAP-02 de
[deployment-gaps.md](../deployment-gaps.md)). Sinon les 100 utilisateurs partagent une
clé de quota. `tests/load/attribution.py` le **prouve avant** la campagne : il épuise
délibérément le quota d'une source puis vérifie qu'une seconde source est toujours
servie ; un 429 sur la seconde fait échouer la préflight avec le diagnostic
« shared: forwarded address ignored », et la campagne ne démarre pas.

Le chemin du refus est mesuré **séparément**, comme A01 l'exige : `refusal_scenario()`
tire depuis une source unique, attend des 429 avec `Retry-After` entier, et ses 429 ne
comptent pas contre le seuil d'erreur. Au plateau au contraire, tout 429 est une erreur
inattendue (`metrics.EXPECTED`) et le taux de 429 est publié à part
(`rate_limited_rate`), afin qu'une campagne dégradée soit visible et non maquillée.

## Procédure exacte pour l'exploitant

Prérequis : VPS de test explicitement autorisé et isolé, aucune donnée réelle, stack
déployée au SHA consigné, proxy de test autorisé configuré, `Q02_SOURCES` sources
distinctes réellement routées. Le harnais refuse toute cible non prouvée jetable :
l'hôte doit être en boucle locale, en adresse privée, ou porter un libellé
`test/tests/staging/preprod/sandbox/qa/local`, et `Q02_TARGET_ACK` doit répéter l'hôte.

```
export Q02_LOAD_TEST=1
export Q02_TARGET_URL=https://api.test.example   # jamais une origine de production
export Q02_TARGET_ACK=api.test.example
export Q02_ORIGIN=https://front.test.example     # origine autorisée de cette stack
export Q02_SEED_PASSWORD=...                     # synthétique, hors dépôt, >=12 car.
export Q02_RUN_ID=2026mmjj-1
export Q02_ACCOUNTS=500 Q02_USERS=100 Q02_SOURCES=100 Q02_PLATEAU_S=1200
uv run --no-sync pytest -q -s -m load tests/load         # environ 35 min
python -m tests.load.cleanup "$Q02_RUN_ID"               # imprime le SQL de purge
```

Aucun secret n'a de valeur par défaut : `Q02_TARGET_URL`, `Q02_ORIGIN`,
`Q02_SEED_PASSWORD`, `Q02_RUN_ID` et `Q02_TARGET_ACK` sont obligatoires et le harnais
échoue en `ProductionTargetRefused` s'ils manquent. La purge n'est jamais exécutée par
le harnais : `tests/load/cleanup.py` imprime un `SELECT count(*)` puis le `DELETE`
correspondant, afin que le rayon d'action soit visible avant qu'un humain l'exécute.

À consigner avec la sortie JSON du harnais : SHA testé, CPU/RAM/disques du VPS,
versions, nombre de workers, réglages de pool, configuration du proxy, graine
(`Q02_SEED`), CPU et RAM par minute, pics de connexions API et `pg_stat_activity`, et
tout OOM. Sans ces relevés la campagne reste partielle, même si les seuils de latence
passent, et le verdict de [load.md](load.md) reste BLOQUÉ.
