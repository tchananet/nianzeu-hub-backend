# Profils, contact et découverte v1 (décisions A01)

## Correspondance Frontend consultative

Enums retenus tels que communiqués : `availability = immediate | 1-week | freelance | full-time`, `experience_level = junior | intermediate | senior` (correspond au champ frontend `experienceLevel`). Ces disponibilités mêlent délai et mode de travail ; v1 les conserve comme valeurs exclusives exactes, sans inférer un délai ou contrat. API snake_case ; aucun alias camelCase implicite.

Téléphone et indicateurs de visibilité sont de nouveaux champs contractuels, pas une compatibilité frontend déjà constatée. Email public nullable et distinct de l'email de connexion ; aucun fallback implicite. `photoHint` est une indication cosmétique frontend, non persistée/non acceptée par API. Pas de photo de profil uploadée au MVP ; portfolio image ne devient pas automatiquement avatar. `useInternalForm` et messagerie/formulaire interne hors MVP : champ inconnu → 422, aucun envoi serveur. Types portfolio frontend `link` hors MVP : voir [portfolio](portfolio.md).

## Schémas

`ProfileWrite` : tous les champs du tableau sont obligatoires dans PUT (les valeurs null sont explicites). Aucune propriété `id`, `user_id`, timestamps ou vues acceptée. PUT remplace les données et toutes les collections dans une transaction ; plafond 64 KiB commun. Les sous-objets n'acceptent pas d'ID client : IDs enfants régénérés au remplacement, aucune URL enfant stable promise.

| Champ | Type et contraintes |
|---|---|
| display_name | chaîne 1..100 |
| headline | chaîne 1..160 |
| bio | chaîne 0..5000, texte brut |
| city | chaîne 1..100 |
| country_code | deux lettres ASCII majuscules, code ISO 3166-1 alpha-2 reconnu par liste figée dans dépendance F01 |
| availability | enum ci-dessus |
| experience_level | enum ci-dessus, autodéclaré sans calcul depuis expériences |
| rate | null ou `{amount:"15000.00",currency:"XAF",unit:"hour"}` |
| skill_ids | tableau UUID uniques, 0..30, existants dans skills |
| experiences | tableau 0..20 de `{title,organization,start_date,end_date,description}` |
| certifications | tableau 0..20 de `{name,issuer,issued_on,expires_on,credential_url}` |
| contacts | objet ContactWrite ci-dessous |

Tarif A01 : amount chaîne décimale sans exposant, deux décimales exactes, 0.01..99999999.99 ; devise **XAF uniquement** au MVP, unité `hour | day | project`. Aucun montant flottant, conversion de devise ou « salaire mensuel » implicite. `rate:null` signifie non renseigné. Pour XAF, fraction non nulle refusée (ex. `15000.50` → 422), sérialisation conserve `.00`. Unités et devise sont retournées ensemble et filtrage tarif hors MVP.

Expérience : title et organization 1..150, description 0..2000 ; start_date valide ≤ date UTC du jour, end_date null signifie expérience actuelle, sinon start_date ≤ end_date ≤ aujourd'hui. Dates complètes `YYYY-MM-DD` ; pas de mois seuls, chaîne vide, `current` ou booléen `isCurrent`. Chevauchements permis. Certification : name/issuer 1..150, issued_on ≤ aujourd'hui ; expires_on null signifie sans expiration connue, sinon ≥ issued_on (date future autorisée) ; credential_url null ou HTTPS ≤2048, sans credentials, uniquement lien jamais récupéré.

`ContactWrite = {email:string|null,phone:string|null,whatsapp:string|null,email_visible:boolean,phone_visible:boolean,whatsapp_visible:boolean}`. Email syntaxe/normalisation identité. Phone/WhatsApp E.164 `+` suivi de 8..15 chiffres, premier non nul ; espaces/format local rejetés. Valeur visible=true nécessite valeur non nulle ; null avec false permis. Aucune vérification de possession promise. Création SQL de contacts par défaut : valeurs null, flags false ; le PUT initial peut choisir explicitement des valeurs publiques.

`ProfileOwner` = `{id,user_id,created_at,updated_at}` + tous champs ProfileWrite ; chaque expérience/certification retournée ajoute `id`, skill_ids conservés, champs contact privés inclus. `ProfilePublic` = `{id,display_name,headline,bio,city,country_code,availability,experience_level,rate,skills,experiences,certifications,contacts,created_at,updated_at}` ; skills objets `{id,name}`, enfants avec id ; aucune adresse de login, user_id ou flag privé. `ContactPublic = {email:string|null,phone:string|null,whatsapp:string|null}` : chaque valeur masquée est null, clés toujours présentes. Même projection pour profil, recherche et contact ; aucun email dans les réponses si non visible. Les clients peuvent produire mailto/tel/wa.me à partir de ces valeurs ; serveur n'envoie aucun message.

## Routes profils et contacts (P01)

| Route sous /api/v1 | Entrée | Résultat | Accès |
|---|---|---|---|
| GET `/profiles/me` | aucune | 200 ProfileOwner, 404 si absent | session |
| PUT `/profiles/me` | ProfileWrite complet | 201 création avec Location `/api/v1/profiles/{id}`, 200 remplacement ; ProfileOwner | session+CSRF |
| DELETE `/profiles/me` | aucune | 204, absent → 404 | session+CSRF |
| GET `/profiles/{profile_id}` | UUID | 200 ProfilePublic ou 404 | anonyme |
| GET `/profiles/me/contacts` | aucune | 200 ContactWrite ou 404 | session |
| PUT `/profiles/me/contacts` | ContactWrite complet | 200 ContactWrite ou 404 | session+CSRF |
| GET `/profiles/{profile_id}/contacts` | UUID | 200 ContactPublic ou 404 | anonyme |
| GET `/skills` | page/page_size, q optionnel 1..80 | 200 collection `{id,name}` | anonyme |
| POST `/profiles/{profile_id}/views` | aucun corps | 204, profil absent 404 | anonyme, Origin/quota |

Routes statiques `/me` enregistrées avant paramètre UUID. Aucun PATCH ni route d'édition d'un profil tiers. Dernière transaction terminée gagne pour PUT concurrents, sans merge implicite ; blocage de ligne profil pendant remplacement/contact pour éviter état hybride. Suppression du profil supprime contacts/enfants/vues et portfolio par cascade ; chaque téléchargement vérifie DB donc retrait immédiat. Les objets orphelins seront nettoyés O01. Recréation après suppression obtient nouvel UUID. Pas de suppression physique MinIO en transaction DB.

Catalogue skills initial fermé, décidé A01/M02 : Python, JavaScript, TypeScript, React, Design graphique, Marketing digital ; UUID fixes recensés dans [data](data.md). Aucune création libre ni admin route. GET skills q fait correspondance sous-chaîne insensible à casse, `%`/`_` littéraux, tri name normalisé puis id. Référence skill inconnue 422 champ skill_ids.

Vues : succès 204 même si dédupliqué, incrément quotidien atomique une fois par profil/IP-HMAC/jour UTC ; pas d'identifiant visiteur/cookie ni IP brute conservée ; compteur non retourné au MVP. Ligne de déduplication expire après 48 h, agrégats après 90 jours. Quota vues appliqué avant déduplication.

## Recherche (R01)

GET `/search/profiles`, anonyme. Query : `q` optionnel trim 1..100 ; `skill_id` répété jusqu'à 10 UUID distincts (AND, tous exigés), `city` 1..100 égalité insensible à casse, `country_code`, `availability`, `experience_level` mêmes contraintes que profil ; `page`, `page_size` communs. Skill inconnu bien formé → liste vide. Aucun filtre sur email/phone/WhatsApp/bio privé. Tri fixe updated_at DESC, id ASC, pas de paramètre sort libre.

q : recherche sous-chaîne insensible à casse dans display_name OU headline OU bio ; accents conservés, `%`, `_`, `\` échappés comme littéraux, SQL paramétré. Autres filtres combinés AND. Pas de classement flou/IA/plein texte promis. À 500 profils, scans bornés acceptés ; M03 ajoute index filtres/tri et jointure skills sans extension PostgreSQL. Réponse collection de `ProfileSummary = {id,display_name,headline,city,country_code,availability,experience_level,rate,skills}` ; aucune coordonnée, expériences ou bio dans résumé. Pour un contact, consulter endpoint public dédié.

Acceptation P01/R01 : PUT création/remplacement/suppression, dates/null et limites tableaux, contacts cachés dans toutes projections, enums stricts, tarif complet ; accès A/B refusé ; recherche AND de deux skills, casse/accents/littéraux, bornes pagination, total exact, tri déterministe ; au plus 5 requêtes SQL par recherche indépendamment de page_size (éviter N+1), timeout commun. Profil supprimé absent recherche et vues. Test vue dédupliquée en concurrence. Aucune route n'émet d'email ni n'accepte useInternalForm.
