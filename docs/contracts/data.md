# Données et migrations v1 — décisions A01

PostgreSQL ; UUID v4 générés serveur, instants timestamptz UTC, dates SQL date. Sauf indication, colonnes NOT NULL ; PK id UUID, created_at/updated_at timestamps pour entités users/profiles/portfolio, created_at pour sessions/uploads/enfants. Les noms ci-dessous sont normatifs. FK vers parent avec ON DELETE CASCADE sauf skills RESTRICT. Transactions pour tout remplacement de collections ; SQL paramétré. Contraintes longueur et bornes simples CHECK en DB ; syntaxe email/URL, dates relatives à aujourd'hui, parsing fichiers et quotas multi-lignes validés service. Aucun index sur coordonnées privées.

## M01 — identité et fondations

| Table | Colonnes / contraintes |
|---|---|
| users | id, email varchar(254) UNIQUE (déjà normalisé, CHECK email=lower(email)), role varchar CHECK ='talent', is_active boolean défaut true, created_at, updated_at |
| credentials | user_id UUID PK FK users, password_hash text (Argon2 encodé), updated_at ; aucun mot de passe brut |
| sessions | id, user_id FK users, token_hash char(64) UNIQUE, csrf_token varchar(43), created_at,last_seen_at,expires_at,revoked_at nullable ; expires_at>created_at ; index (user_id,created_at), index expires_at |
| password_reset_tokens | id,user_id FK users,token_hash char(64) UNIQUE,created_at,expires_at,used_at nullable ; expires_at>created_at ; table vide au MVP, aucun endpoint ne crée/consomme de token |
| rate_limit_windows | scope varchar(40),key_hash char(64),window_start timestamptz,expires_at timestamptz,count integer CHECK >=0 ; PK(scope,key_hash,window_start), index expires_at |

CSRF est secret synchronisé consultable par le propriétaire de session, DB restreinte ; token de session et reset stockés seulement hashés. Primitives quotas F01 testées par fixture DDL isolée correspondant au contrat, schéma production uniquement par M01. Readiness F02 ne consulte pas ces tables.

## M02 — profils et contact

| Table | Colonnes / contraintes |
|---|---|
| talent_profiles | id,user_id FK users UNIQUE,display_name varchar(100),headline varchar(160),bio varchar(5000),city varchar(100),country_code char(2),availability varchar(16),experience_level varchar(16),rate_amount numeric(10,2) nullable,rate_currency char(3) nullable,rate_unit varchar(10) nullable,created_at,updated_at |
| skills | id,name varchar(80),normalized_name varchar(80) UNIQUE ; nom normalisé lower(name) |
| profile_skills | profile_id FK talent_profiles,skill_id FK skills RESTRICT ; PK(profile_id,skill_id) |
| experiences | id,profile_id FK talent_profiles,title varchar(150),organization varchar(150),description varchar(2000),start_date date,end_date date nullable,position smallint CHECK 0..19,created_at ; UNIQUE(profile_id,position), CHECK end_date IS NULL OR end_date>=start_date |
| certifications | id,profile_id FK talent_profiles,name varchar(150),issuer varchar(150),issued_on date,expires_on date nullable,credential_url varchar(2048) nullable,position smallint CHECK 0..19,created_at ; UNIQUE(profile_id,position), CHECK expires_on IS NULL OR expires_on>=issued_on |
| contact_settings | profile_id PK FK talent_profiles,email varchar(254) nullable,phone varchar(16) nullable,whatsapp varchar(16) nullable,email_visible/phone_visible/whatsapp_visible boolean défaut false ; chaque flag true exige valeur non nulle |
| profile_views | profile_id FK talent_profiles,day date,count integer CHECK >=0 ; PK(profile_id,day) |
| profile_view_dedup | profile_id FK talent_profiles,day date,visitor_hash char(64),expires_at timestamptz ; PK(profile_id,day,visitor_hash), index expires_at |

CHECK availability IN ('immediate','1-week','freelance','full-time'), experience_level IN ('junior','intermediate','senior'). Rate : trois colonnes toutes null ou toutes renseignées, amount>0 et <=99999999.99, currency='XAF', amount=trunc(amount), unit IN ('hour','day','project'). Chaînes requises non vides sauf bio/description. Collections ordonnées par position ; skills tri normalized_name,id. Une ligne contact créée atomiquement avec profil. Unicité user_id protège création concurrente (une 201, l'autre mise à jour 200 après verrou utilisateur).

Seed skills déterministe M02 (UUID/name) :

| UUID | Nom |
|---|---|
| 00000000-0000-4000-8000-000000000001 | Python |
| 00000000-0000-4000-8000-000000000002 | JavaScript |
| 00000000-0000-4000-8000-000000000003 | TypeScript |
| 00000000-0000-4000-8000-000000000004 | React |
| 00000000-0000-4000-8000-000000000005 | Design graphique |
| 00000000-0000-4000-8000-000000000006 | Marketing digital |

## M03 — portfolio et index recherche

| Table | Colonnes / contraintes |
|---|---|
| portfolio_items | id,profile_id FK talent_profiles,title varchar(160),description varchar(2000),type varchar(8),state varchar(12),created_at,updated_at,validated_at/published_at nullable,object_key varchar(255) nullable UNIQUE,filename varchar(120) nullable,media_type varchar(80) nullable,size_bytes bigint nullable,sha256 char(64) nullable,rejection_code varchar(40) nullable |
| portfolio_uploads | id,item_id FK portfolio_items UNIQUE,quarantine_key varchar(255) UNIQUE,filename varchar(120),media_type varchar(80),size_bytes bigint CHECK >0,sha256 char(64),created_at,expires_at,lease_until nullable,reservation_active boolean ; expires_at>created_at |

Ligne upload courante unique/item remplacée lors d'une nouvelle tentative rejected ; ancien objet devient orphelin. CHECK type IN ('image','pdf','video'), state IN ('draft','pending','validating','rejected','validated','published'). État validated/published exige toutes métadonnées finales et validated_at non null ; autres états les gardent null. published exige published_at non null ; unpublish remet published_at null. CHECK size_bytes NULL ou 1..104857600, bornes spécifiques type au service. Validation conserve upload_id pour idempotence, reservation_active=false à succès/rejet/expiration. Lease non nulle seulement pendant validation (effacée en sortie). Index (profile_id,state,published_at,id).

Index M03 : talent_profiles(updated_at DESC,id ASC), (availability), (experience_level), (country_code,lower(city)), profile_skills(skill_id,profile_id). FK enfants indexées par leur préfixe profile_id ; sessions par user_id. q sous-chaîne reste scan borné à la cible 500 comptes ; aucune extension pg_trgm requise. Tester plan EXPLAIN et nombre de requêtes, pas imposer artificiellement un index sur petite table.

## Registre de migration séquentiel

| Mission / revision | down_revision | Contenu | Preuves obligatoires en DB jetable |
|---|---|---|---|
| M01 / 0001_identity | null | alembic.ini/env, tables identité/quotas | vide → upgrade → downgrade base → upgrade ; uniques/FK/checks, sessions |
| M02 / 0002_profiles | 0001_identity | profils/contacts/skills/vues + seed | fixture users/sessions M01 conservée ; upgrade → downgrade 0001 → upgrade ; contraintes et seed |
| M03 / 0003_portfolio_search | 0002_profiles | portfolio/uploads et index | fixtures identité/profils/contacts M02 conservées ; upgrade → downgrade 0002 → upgrade ; index/checks |

Un seul propriétaire migrations, une seule tête. Downgrades destructifs réservés aux bases jetables ; jamais stratégie de rollback production automatique. Les fixtures des tables introduites par une révision peuvent être perdues au downgrade ; conservation exigée pour tables des révisions antérieures. Migrations DDL autonomes, sans import des modules encore absents. Modèles ORM livrés I01/P01/O01 doivent correspondre au DDL ; différences bloquent QA et nécessitent mission dédiée, aucune migration cachée de module.

Entretien via services concernés : fenêtres quotas >24 h purgées F01/I01 ; dédup vues >48 h et agrégats >90 jours P01 ; uploads/orphelins O01. Suppressions de profil en cascade immédiates ; aucun objet MinIO ne devient public par seule présence en stockage. Les quotas d'octets/items sont calculés sous verrou users depuis items/uploads (pas de compteur divergent).
