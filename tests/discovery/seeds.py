from datetime import UTC, datetime, timedelta

from app.modules.discovery.schemas import SearchQuery
from app.modules.discovery.service import DiscoveryService
from app.modules.profiles.schemas import ProfileWrite
from app.modules.profiles.service import ProfilesService

PYTHON = "00000000-0000-4000-8000-000000000001"
REACT = "00000000-0000-4000-8000-000000000004"
DESIGN = "00000000-0000-4000-8000-000000000005"
MARKER = "r01seed"
BASE = datetime(2026, 1, 1, tzinfo=UTC)
VISIBLE_CONTACTS = dict(email="public@example.com", phone="+237600000001",
                        whatsapp="+237600000002", email_visible=True,
                        phone_visible=True, whatsapp_visible=True)


def payload(**overrides):
    """Every seed publishes visible contacts: search must still never return them."""
    values = dict(
        display_name="Ada Lovelace", headline="Python developer", bio=MARKER,
        city="Douala", country_code="CM", availability="immediate",
        experience_level="senior", rate=None, skill_ids=[PYTHON],
        experiences=[], certifications=[], contacts=dict(VISIBLE_CONTACTS),
    )
    values.update(overrides)
    return values


SEEDS = (
    ("ada", 10, payload()),
    ("grace", 10, payload(display_name="Grace Hopper", headline="React engineer",
                          bio=f"{MARKER} loves 100% design", city="DOUALA",
                          availability="freelance", experience_level="junior",
                          skill_ids=[PYTHON, REACT])),
    ("alan", 20, payload(display_name="Alan Turing", headline="Designer",
                         bio=f"{MARKER} ada of maths", city="Yaoundé",
                         skill_ids=[DESIGN],
                         rate=dict(amount="15000.00", currency="XAF", unit="hour"))),
    ("linus", 30, payload(display_name="Linus", headline="DevOps", bio=MARKER,
                          city="Paris", country_code="FR", availability="full-time",
                          experience_level="intermediate", skill_ids=[])),
)


def seed_profiles(factory, user_ids):
    seeded = {}
    for (name, offset, data), user_id in zip(SEEDS, user_ids, strict=True):
        moment = BASE + timedelta(minutes=offset)
        service = ProfilesService(factory, clock=lambda fixed=moment: fixed)
        owner, _ = service.put(user_id, ProfileWrite.model_validate(data))
        seeded[name] = (user_id, owner.id)
    return seeded


def search(factory, **kwargs):
    return DiscoveryService(factory).search(SearchQuery.model_validate(kwargs))


def names(seeded, page):
    reverse = {profile_id: name for name, (_, profile_id) in seeded.items()}
    return [reverse.get(item.id, f"foreign:{item.id}") for item in page.items]
