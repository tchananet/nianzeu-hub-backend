"""Single place where the feature modules are composed into one application.

Each module exposes ``create_router`` and receives its collaborators explicitly, so
composition stays here and no module reaches for a global. The one ``ProfileAccess``
instance is shared on purpose: profiles, contact and search must consume the same
``public_json`` request quota group rather than one counter each.
"""

from fastapi import APIRouter
from sqlalchemy import Engine

from app.core.config import Settings
from app.core.database import session_factory
from app.modules.contact import routes as contact_routes
from app.modules.contact.service import ContactService
from app.modules.discovery import routes as discovery_routes
from app.modules.discovery.service import DiscoveryService
from app.modules.identity import routes as identity_routes
from app.modules.identity.browser import BrowserPolicy
from app.modules.identity.limits import IdentityLimits
from app.modules.identity.passwords import Passwords
from app.modules.identity.principal import IdentityPrincipalResolver
from app.modules.identity.service import IdentityService
from app.modules.profiles import routes as profiles_routes
from app.modules.profiles.access import ProfileAccess
from app.modules.profiles.service import ProfilesService
from app.modules.profiles.views import ViewsService


def build_routers(settings: Settings, engine: Engine) -> list[APIRouter]:
    factory = session_factory(engine)
    secret = settings.quota_hmac_secret.get_secret_value()
    browser = BrowserPolicy(settings)
    identity = IdentityService(factory, Passwords())
    resolver = IdentityPrincipalResolver(identity, browser)
    access = ProfileAccess(resolver, browser, factory, secret)
    return [
        identity_routes.create_router(identity, IdentityLimits(factory, secret), browser),
        profiles_routes.create_router(ProfilesService(factory), ViewsService(factory), access),
        contact_routes.create_router(ContactService(factory), access),
        discovery_routes.create_router(DiscoveryService(factory), access),
    ]
