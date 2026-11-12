# Exceptions de taille

| Chemin | Catégorie | Motif | Générateur / commande |
|---|---|---|---|
| uv.lock | lock généré | Résolution intégrale, versions et hashes reproductibles | uv 0.11.6 ; `uv lock --python 3.13` (initialement généré par `uv sync --python 3.13`) |

Aucune exception pour sources/tests manuels ; chaque fichier Python doit rester sous 100 lignes.
Documentation hors plafond. .venv et caches locaux ignorés, non livrables, jamais versionnés.
