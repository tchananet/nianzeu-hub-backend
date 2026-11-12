# nianzeu-hub-backend

Backend autonome de Nianzeu Hub.

Stack validée : Python, FastAPI, PostgreSQL, SQLAlchemy, Alembic et MinIO.
Déploiement avec Docker Compose sur VPS derrière Nginx Proxy Manager.

MVP : comptes talents, authentification email/mot de passe, profils publics,
recherche et portfolios. Les visiteurs peuvent consulter et contacter les talents
sans compte. OAuth et messagerie interne sont prévus après le MVP.

Statut : architecture validée, implémentation à déléguer aux agents spécialisés.
