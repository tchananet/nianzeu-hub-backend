# Q02 — charge : harnais livré, **aucune mesure prise**

**Verdict : BLOQUÉ.** Aucun chiffre de p95, de débit, d'erreur, de CPU/RAM ni de
connexions n'existe pour ce dépôt. La condition d'entrée du plan — « VPS de test
disponible » (plan.md, ligne Q02) — n'est pas remplie : l'environnement de cette mission
n'a ni VPS autorisé, ni démon Docker, ni base PostgreSQL. Ce document livre le harnais
prêt à tourner ; il ne livre pas de résultat. Toute valeur chiffrée présentée ailleurs
comme un résultat Q02 serait une invention.

Mélange de parcours, traitement des quotas et procédure exacte pour l'exploitant :
[load-procedure.md](load-procedure.md). Harnais : `tests/load/`.

## Seuils fixés par A01 — cités, non inventés

Source unique : [contracts/verification.md](../contracts/verification.md), section
« Q02 charge — décision A01 à mesurer ultérieurement ». Extrait littéral :

> Seuils plateau : p95 lectures JSON ≤500 ms, p95 mutations ≤1000 ms ; erreurs
> inattendues <1% (inclut timeout, 5xx, 429 non prévus), aucune fuite ni erreur
> intégrité ; débit réalisé ≥25 requêtes/s, pas de diminution >20% entre première et
> dernière tranche 5 min. CPU moyenne <80%, RAM <85%, aucun OOM, connexions API ≤20 et
> total DB ≤40. Relever aussi p99, débit, nombre erreurs, CPU/RAM chaque minute.

Scénario, du même paragraphe : « 5 minutes échauffement, 5 minutes montée linéaire
0→100 utilisateurs, 20 minutes à 100, 2 minutes descente », « 500 comptes synthétiques
avec profils, contacts publics/privés et petits portfolios », « 1..3 secondes entre
parcours ». Le budget de connexions vient d'[architecture.md](../architecture.md) : deux
workers, pool 5 + overflow 5, « maximum 20 connexions API ; PostgreSQL budget total 40 »
— et le même paragraphe précise que « ces nombres sont hypothèses A01 à mesurer Q02 ».

Les seuils de latence, d'erreurs et de débit sont codés dans `tests/load/thresholds.py`
avec la citation en en-tête ; les phases dans `tests/load/phases.py`. CPU, RAM, OOM et
connexions **ne sont pas** observables depuis le générateur : `tests/load/report.py` les
émet en `null` sous `not_measured_by_harness`, à remplir par l'exploitant depuis l'hôte
et `pg_stat_activity`. Le harnais ne peut donc pas prononcer seul un PASS Q02 complet.

## Ce qui est réellement vérifié ici

Commandes exécutées dans ce worktree, PostgreSQL absent de la machine :

```
python -m ruff check .                  # code 0, « All checks passed! »
python -m mypy app                      # code 0, 104 fichiers
python -m pytest -q                     # 486 réussis, 5 ignorés, 246 erreurs
python -m pytest -q --ignore=tests/load # 465 réussis, 2 ignorés, 246 erreurs
python -m pytest -q -m load             # 3 ignorés, 734 désélectionnés
```

Les 246 erreurs sont antérieures et identiques avec ou sans `tests/load` : toutes sont
des `BLOQUÉ : *_TEST_DATABASE_URL requis`, l'environnement n'ayant pas de PostgreSQL.
`tests/load` ajoute 21 tests hors-ligne réussis et 3 tests de campagne **collectés puis
ignorés** : le comportement de `pytest -q` est inchangé. Le double verrou est le marqueur
`load`, déclaré par `tests/load/conftest.py` puisque `pyproject.toml` n'appartient pas à
Q02, et la variable `Q02_LOAD_TEST=1`.

Les 21 tests hors-ligne (`test_harness_offline.py`, `test_report_offline.py`) prouvent le
garde-fou de cible (hôtes jetables acceptés, `api.diddifree.com` refusé, `from_env` lève
`ProductionTargetRefused`), la somme du mélange à 100, l'identifiabilité du corpus et sa
répartition sur les sources, la complétude du corps `ProfileWrite`, le budget
d'inscriptions, les percentiles au rang le plus proche, les quatre phases A01 et leur
nombre d'utilisateurs actifs, le fait qu'un 429 au plateau compte comme erreur et fait
échouer le verdict, le rendu JSON d'une campagne synthétique avec ses lacunes hôte en
`null`, et que le SQL de purge ne vise que le préfixe du run.

## Ce qui reste à faire — à ne pas présenter comme acquis

- **La mesure elle-même.** Aucun p95, p99, débit, taux d'erreur, CPU, RAM, OOM ni
  comptage de connexions. Les hypothèses A01 de 20 connexions API et 40 DB restent des
  hypothèses, et le coût Argon2 au login reste non chiffré.
- **Le scénario fichiers** (10 utilisateurs, image 1 MiB / PDF 5 MiB / vidéo 20 MiB,
  p95 validation ≤30 s) n'est pas implémenté : il exige MinIO réel, hors de portée ici.
- **Le relevé CPU/RAM/connexions par minute** n'est pas automatisé ; il est à produire
  côté hôte et à joindre au JSON du harnais.
- **Le harnais n'a jamais parlé à une API réelle.** Les formes de requêtes viennent de la
  lecture du code (`app/modules/*/routes.py`, schémas) et des contrats, pas d'un
  aller-retour observé. Première campagne : s'attendre à corriger des détails de corps ou
  d'en-têtes, et traiter un échec d'amorçage comme un défaut du harnais, pas du produit,
  jusqu'à preuve du contraire.
- **Conséquence pour D01** ([qa/release.md](release.md)) : la preuve de charge exigée par
  les conditions de sortie du plan n'existe pas. Q02 ne lève aucune condition de fusion
  ni de livraison MVP.
