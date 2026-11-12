# Gate de livraison production — inventaire des preuves

Document D01 (Architect). **Synthèse, pas verdict** : `docs/ownership.md` réserve le verdict
signé à QA. Aucun élément ci-dessous n'est auto-validé ; les statuts sont constatés par
lecture du dépôt au SHA de base `6e827ff` et de `docs/qa/`, pas déclarés.

Légende : **PROUVÉ** = rapport QA indépendant présent dans `docs/qa/` ; **FUSIONNÉ SANS
RAPPORT** = code sur `main` mais aucun rapport QA enregistré ; **ABSENT** = livrable
inexistant dans le dépôt.

## 1. Fondations, contrats et code

| Preuve attendue | Mission | Statut constaté | Référence |
|---|---|---|---|
| Contrats API/données/sécurité v1 figés | A01 | **PROUVÉ** (verdict QA, fusion `9ae4a0d`) | `docs/qa/A01.md` |
| Configuration fail-fast, ports, quotas atomiques, PostgreSQL réelle | F01 | **PROUVÉ** à distance : 53 tests, 0 skip, Ruff/Mypy verts, PyAV 17.1.0, deux exécutions indépendantes | `docs/qa/F01-REMOTE.md` |
| Image verrouillée, Compose isolable, buckets privés, persistance après redémarrage | F02 | **FUSIONNÉ SANS RAPPORT** : aucun `docs/qa/F02.md`, aucun build/démarrage consigné | `Dockerfile`, `docker-compose.yml` |
| Migration identité, une tête, aller-retour en base jetable | M01 | **FUSIONNÉ SANS RAPPORT** | `migrations/versions/0001_identity.*` |
| Migration profils/contacts/compétences, conservation des données | M02 | **FUSIONNÉ SANS RAPPORT** | `migrations/versions/0002_profiles*.sql` |
| Inscription, login/logout/me, sessions révocables, CSRF, reset 503 | I01 | **FUSIONNÉ SANS RAPPORT** | `app/modules/identity/` |
| CRUD profil propriétaire, lecture anonyme, visibilité des contacts | P01 | **FUSIONNÉ SANS RAPPORT** | `app/modules/profiles/`, `app/modules/contact/` |
| Migration portfolio et index recherche (`0003_portfolio_search`) | M03 | **ABSENT** : seul un commit documentaire existe, aucune révision | `docs/missions/M03.md` |
| Recherche anonyme paginée et bornée | R01 | **ABSENT** : `app/modules/discovery/` inexistant | — |
| Uploads validés, publication après validation, nettoyage | O01 | **ABSENT** : `app/modules/portfolio/` inexistant | — |
| Routes assemblées et parcours de bout en bout | X01 | **ABSENT** : `app/main.py` n'expose que les deux routes de santé | `app/main.py` |

## 2. Qualité, sécurité et capacité

| Preuve attendue | Mission | Statut constaté |
|---|---|---|
| `ruff check .`, `mypy app`, `pytest` complet au SHA livré | auteur de chaque mission | **à refaire au SHA de livraison** ; la dernière suite prouvée indépendamment est celle de F01 (53 tests), antérieure à I01/P01 |
| `docker compose config --quiet` et `docker compose build` au SHA livré | F02 | **non consigné** par un rapport QA |
| `alembic heads` unique et `alembic upgrade head` sur PostgreSQL réelle au SHA livré | propriétaire migrations | **non consigné** ; tête actuelle `0002_profiles`, `0003` manquante |
| Contrôle sécurité indépendant (sessions, accès tiers, uploads, fuites, reset désactivé) | Q01 | **ABSENT** : ni `tests/security/` ni `docs/qa/security.md` |
| Charge : 500 comptes, 100 simultanés, p95 ≤ 500 ms / ≤ 1000 ms, erreurs < 1 %, CPU < 80 %, RAM < 85 %, connexions ≤ 20/≤ 40 | Q02 | **ABSENT** : ni `tests/load/` ni `docs/qa/load.md` ; aucune mesure, aucun chiffre revendiqué |
| Sauvegarde cohérente base + objets, rétention, restauration répétée, RPO/RTO mesurés | B01 | **ABSENT** : ni `ops/backup/` ni `docs/backup.md` ; RPO ≤ 24 h et RTO ≤ 4 h restent des cibles A01 |
| Runbook d'exploitation Compose/NPM, migrations, santé, nettoyage, retour arrière | D01 | **LIVRÉ, en attente de revue QA** : `docs/deployment.md` et ses cinq annexes |

## 3. Contrôles transverses exigés par le plan

| Contrôle | Statut |
|---|---|
| Diff limité à l'ownership de la mission | D01 : `docs/deployment*.md`, `docs/qa/release.md`, `docs/missions/D01.md` seulement |
| Sources manuelles et tests < 100 lignes | aucun fichier source ajouté par D01 ; registre inchangé (`docs/exceptions.md`) |
| Aucun secret versionné | `.gitignore` exclut `.env`/`.env.*` sauf `.env.example`, qui ne contient que des placeholders ; les documents D01 n'emploient que des marqueurs `<…>` |
| Aucun déploiement ni changement d'infrastructure par la mission | respecté : aucun appel Docker, Compose, Alembic ou Portainer exécuté par D01 |

## 4. Blocages de livraison

1. **Dépendances propres de D01 non satisfaites.** `plan.md` conditionne D01 à la fusion de
   Q02 et B01 ; aucune des deux n'existe. Le critère d'acceptation « QA valide preuves
   Q02/B01 » est donc intenable : D01 est livrée comme runbook documentaire, et la synthèse
   de ce gate ne peut pas conclure positivement.
2. **Périmètre MVP incomplet** : M03, R01, O01 et X01 absents. Un déploiement actuel ne
   servirait que `/health/live` et `/health/ready` (GAP-13).
3. **Blocages d'exploitation** recensés dans [../deployment-gaps.md](../deployment-gaps.md) :
   GAP-01 (joignabilité depuis NPM), GAP-02 (quotas par IP écrasés par le proxy) et GAP-12
   (aucune sauvegarde ni restauration) interdisent une exposition publique.
4. **Preuves QA manquantes** pour F02, M01, M02, I01 et P01, alors que leur code est déjà sur
   `main` : à reprendre au SHA de livraison, jamais à présumer.

## 5. Conditions de passage du gate

Le gate n'est franchissable que lorsque, cumulativement : les quatre missions de périmètre
manquantes sont livrées et validées ; Q01, Q02 et B01 fournissent des rapports QA avec
commandes, codes de sortie et mesures réelles ; GAP-01, GAP-02 et GAP-12 sont résolus par les
missions propriétaires ; la suite complète, `docker compose config/build` et
`alembic upgrade head` sont reproduits par QA au SHA exact de livraison ; et QA signe un
verdict dans ce fichier. Tant qu'une seule de ces lignes manque, la livraison production
reste **bloquée**, et aucun report ne vaut succès.
