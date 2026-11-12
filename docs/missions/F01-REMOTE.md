# F01-REMOTE — Backend, harness isolé

Base : `86822068afe71d7a0116d2267c13785a6b64c1d2` (main propre).
Candidat testé exclusivement : `6d3cd45cb4f9b7685cbda06bf4ecaf9207d44c05`.
Branche : `test/f01-remote-harness`, worktree : `worktrees/F01-REMOTE`.
Ownership : `ops/test-portainer/` et cette fiche uniquement.
Dépendances : contrats A01, candidat F01 distant, inspection parent et QA indépendante.
Livrables : Compose autonome avec runner/préflight inline ; rendu statique `run.sh`.
Critères : installation locked complète Python 3.13, import PyAV, Ruff, Mypy,
pytest ciblé puis complet sur PostgreSQL réel ; aucun succès anticipé.

## Isolation et limites

Cible déclarée par le parent : endpoint 3 `diddifree-prod`, Docker 29.6.2,
Linux amd64, 12 CPU, 47 GiB, 89 conteneurs existants ; inspection non reproduite ici.
Le projet neuf `nianzeu-f01-remote-6d3cd45` possède son réseau et son volume work.
Aucun port publié, réseau/volume externe, montage hôte/socket ou mode privilégié.
PostgreSQL écoute seulement loopback ; le runner partage son namespace réseau.
DB `f01_test`, identifiants synthétiques réservés à cette stack, schémas fixtures jetables.
Rôle applicatif f01 non-superuser, sans création de DB/rôle, propriétaire de sa DB seule.
PostgreSQL : 0.5 CPU / 512 MiB, données tmpfs 256 MiB ; runner : 1 CPU / 2 GiB.
Logs bornés à 2 × 5 MiB par service ; aucun redémarrage automatique.
Timeout runner 900 s, SIGKILL après 10 s supplémentaires, échec propagé.
Les pulls précèdent ce timeout ; aucun délai global de téléchargement garanti.
Images par tags : enregistrer leurs digests effectifs dans les preuves QA.
Le volume work conserve source/venv pour inspection ; relance refusée tant qu'il existe.

## Exécution ultérieure par le parent, après QA

Ne rien déployer maintenant. Aucun push, merge, installation locale ni CI/CD réalisé.
Via Portainer MCP, créer une stack neuve avec le contenu intégral de compose.yaml.
Aucun fichier externe ni variable d'attestation requis ; run.sh ne fait que du rendu.
Le parent vérifie l'absence de collision de nom stack/réseau/volume avant création.
Le runner exige 8 GiB libres sur /work et 6 GiB MemAvailable avant fetch/install.
Les images sont nécessairement téléchargées avant ce préflight, PostgreSQL déjà lancé.
statvfs mesure le filesystem du volume /work, pas tous les disques hôte ; /proc/meminfo
indique la mémoire hôte exposée, pas la marge cgroup. Ce sont des indices non réservés.
Le parent complète par les métriques serveur disponibles ; aucun accès hôte supposé.
Utiliser Docker Standalone Compose, pas Swarm (network_mode service requis).
Dans Portainer, le parent arrête PostgreSQL après chaque sortie du runner.
Ne pas relancer automatiquement un runner sorti ; inspecter son code et ses logs.

Collecter logs runner, code de sortie, SHA checkout, versions/digests et préflight.
Le runner imprime SHA256 du tar `git archive HEAD`, de uv.lock, et version uv.
QA vérifie aussi via inspect les CPU, Memory, PidsLimit et LogConfig effectifs.
Un code 0 avec 53 passed et zéro skip dans chaque suite est nécessaire ; timeout, OOM,
fetch/install manqué,
skip ou tests incomplets ne valident pas F01. QA inspecte les résumés pytest.
Avant nettoyage, conserver les preuves hors volume jetable.
Nettoyage par le parent via Portainer : retirer uniquement cette stack et son volume work.
Les données de test sont irrécupérables sans copie. QA reproduit avec un nouveau nom
de stack et un volume neuf ; ne jamais réutiliser celui de l'auteur.

## Vérification de cette livraison

`git ls-remote` sans credential helper confirme le SHA candidat distant accessible.
Contrôles locaux réussis : Compose config --quiet, bash -n du helper et des deux
commandes inline rendues, diff --cached --check ; ownership limité aux trois fichiers.
Tailles : compose 77 lignes, helper 6, fiche sous 100. Aucun test applicatif local.
Les résultats runtime et le verdict F01 restent bloqués jusqu'à exécution distante et QA.
Cicero `01a1cfaf-1394-7a53-906e-c3fc66bddf0c` doit recevoir le SHA harness du parent :
aucun outil de communication inter-agent disponible dans cette session.
