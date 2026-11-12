from fastapi import APIRouter, Depends, Request, Response

from app.modules.discovery.access import PublicReads
from app.modules.discovery.parsing import parse_search
from app.modules.discovery.responses import ProfileSummary
from app.modules.discovery.service import DiscoveryService
from app.modules.profiles.access import private_headers
from app.modules.profiles.transport import reject_body
from app.shared.dto import Page


def create_router(service: DiscoveryService, access: PublicReads) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    @router.get("/search/profiles", dependencies=[Depends(reject_body)])
    def search(request: Request, response: Response) -> Page[ProfileSummary]:
        # Quota before validation, per the control order of http.md.
        access.public_limit(request)
        private_headers(response)
        return service.search(parse_search(request))

    return router
