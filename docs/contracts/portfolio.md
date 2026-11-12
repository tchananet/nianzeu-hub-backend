# Portfolio v1 — décisions A01

MVP : image/pdf/video uploadés. Le type frontend `link` est hors MVP (422), sans récupération d'URL externe. Aucun éditeur de métadonnées supplémentaire : supprimer/recréer un item pour le modifier.

## Routes sous /api/v1

Toutes les routes privées exigent session ; mutations exigent CSRF et Origin. Item tiers/absent : 404. Profil requis pour création/upload : 409 PROFILE_REQUIRED. UUID partout.

| Route | Entrée | Succès |
|---|---|---|
| POST /profiles/me/portfolio | {title,description,type} | 201 ItemOwner, Location vers lecture privée |
| GET /profiles/me/portfolio | page/page_size | 200 collection ItemOwner |
| GET /profiles/me/portfolio/{item_id} | aucune | 200 ItemOwner |
| POST /profiles/me/portfolio/upload-url | {item_id,filename,media_type,size_bytes,sha256} | 200 {upload_id,method:"POST",url,fields,expires_at} |
| POST /profiles/me/portfolio/{item_id}/validate | {upload_id} | 200 ItemOwner validé |
| POST /profiles/me/portfolio/{item_id}/publish | aucun corps | 200 ItemOwner publié |
| POST /profiles/me/portfolio/{item_id}/unpublish | aucun corps | 200 ItemOwner validé |
| DELETE /profiles/me/portfolio/{item_id} | aucun corps | 204 |
| GET /profiles/{profile_id}/portfolio | page/page_size | 200 collection ItemPublic, anonyme ; profil absent 404 |
| GET /portfolio/{item_id}/content | aucune | 200 flux, anonyme seulement si publié, sinon 404 |

Title 1..160, description 0..2000, type enum image/pdf/video. ItemOwner : {id,profile_id,title,description,type,state,created_at,updated_at,validated_at:null|instant,published_at:null|instant,file:null|FileInfo,rejection_code:null|string}. FileInfo : {filename,media_type,size_bytes,sha256}. ItemPublic : {id,profile_id,title,description,type,published_at,file,content_url}. URL relative vers route content ; aucune clé stockage dans DTO hors champs du formulaire présigné. Liste privée tri created_at DESC,id ASC ; publique published_at DESC,id ASC, seulement published. Pagination commune.

## Validation et quotas

| Type | Extension et MIME exacts | Maximum |
|---|---|---|
| image | .jpg/.jpeg image/jpeg ; .png image/png ; .webp image/webp | 10 MiB |
| pdf | .pdf application/pdf | 20 MiB |
| video | .mp4 video/mp4 | 100 MiB |

MiB = 1048576 octets ; taille entière 1..maximum, SHA-256 hex lowercase 64 caractères. Filename basename 1..120 caractères, sans slash, antislash, contrôle, séquence ".." ni point initial. Extension insensible à casse. Clé jamais fournie par client. Vérifier signature réelle et parsing du format, pas seulement Content-Type. Images : décodage intégral, ≤25 millions pixels ; PDF : parsing, ≤100 pages, refuser chiffrement, JavaScript/actions automatiques et fichiers embarqués ; MP4 : parsing conteneur, durée ≤120 s, vidéo H.264 ≤1920×1080 (orientation inverse admise), audio optionnel AAC. Pas de garantie antivirus/modération. Décodeurs maintenus et verrouillés par F01, sans réseau ; dépendances système prévues au Dockerfile F02. Timeout validation 30 s et mémoire 128 MiB : dépassement rejet VALIDATION_LIMIT.

20 items maximum tous états et 200 MiB par propriétaire pour fichiers validés + réservations actives. Verrou utilisateur pour réserver/libérer atomiquement ; quota dépassé 409 QUOTA_EXCEEDED. Une réservation égale size_bytes annoncé. Maximum une réservation active/item. Pas de remplacement de fichier validé/publié.

## Machine d'état

États : draft → pending → validating → validated → published ; validating peut devenir rejected ; rejected → pending avec nouvelle URL ; published → validated par unpublish. Delete permis dans tout état. Transition illégale 409 INVALID_STATE. Publish déjà publié et unpublish déjà validé sont idempotents, sans changement des timestamps.

1. Création : draft. upload-url seulement draft/rejected ; crée upload UUID et clé aléatoire quarantaine, réservation ; état pending. Formulaire MinIO POST signé 5 minutes, bucket privé, clé exacte, MIME exact, content-length-range min=max=size_bytes. URL fixe issue configuration HTTPS ; fields opaques transmis tels quels. POST MinIO réussi 204 ; ses erreurs S3/XML ne suivent pas l'enveloppe API.
2. validate exige upload courant et non expiré ; prend verrou item, passe validating avec lease 60 s puis libère transaction avant I/O. Objet absent : 409 et retour pending ; expiration : rejected, réservation libérée, 409 UPLOAD_EXPIRED. Validation simultanée : 409. Vérifier taille réelle, SHA, MIME, extension, parsing. Contenu invalide : rejected, réservation libérée, 400 INVALID_UPLOAD ; taille 413 FILE_TOO_LARGE ; format interdit 415 UNSUPPORTED_MEDIA_TYPE.
3. Copier vers une nouvelle clé privée immutable validated, avec condition sur ETag source ; **recalculer SHA et valider la copie finale** avant commit. Le formulaire ne peut écrire que la quarantaine : sa réutilisation ne remplace jamais le fichier final. ETag n'est pas un hash SHA. Commit validated avec clé finale et métadonnées, conversion réservation en taille consommée, seulement si lease/upload/profil existent toujours. Même upload déjà validé → 200 idempotent, autre upload → 409.
4. Publish exige validated et objet final présent (HEAD taille), puis published_at UTC. Public content vérifie DB à chaque lecture et sert le bucket privé via API : jamais d'URL GET signée, bucket/listing public interdits. Unpublish/delete invalident immédiatement les nouvelles lectures ; un flux commencé peut finir et les copies déjà téléchargées ne sont pas révocables.

Panne stockage : 503 DEPENDENCY_UNAVAILABLE, retour pending si lease détenue ; saturation : 503 VALIDATION_BUSY sans changement. Lease expirée récupérable. Suppression concurrente gagne ; finalisation ne recrée jamais profil/item. Objet orphelin après échec à nettoyer. Aucun upload sur disque conteneur.

Nettoyage O01 : commande `uv run --python 3.13 python -m app.modules.portfolio.cleanup --once`, idempotente, planifiée chaque heure par D01. Expire réservations/pending périmés, marque rejected les validating dont lease expirée ; supprime quarantaine >24 h et objets finaux non référencés >24 h après nouvelle vérification DB. DB indisponible : aucune suppression. Les clés ne sont jamais réutilisées. Delete retire DB d'abord ; échec suppression physique journalisé et repris par nettoyage. Profil supprimé cascade les items, même stratégie.

Content : Content-Type validé, Content-Length exact, Content-Disposition attachment avec filename sûr, X-Content-Type-Options nosniff, Cache-Control no-store. MVP téléchargement complet uniquement : Range ignoré avec réponse 200 complète, aucune promesse streaming vidéo seek. Objet publié manquant : 503 et log explicite.

Preuves O01 : publication avant validation refusée, fichiers tiers 404, faux MIME/hash/extensions/taille/parsing rejetés ; overwrite quarantaine sans effet sur copie finale ; concurrence quotas et validation ; panne stockage, lease expirée, suppression concurrente ; bucket privé ; retrait public après unpublish/delete ; aucun fichier local.
