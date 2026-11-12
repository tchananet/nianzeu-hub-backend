from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from app.modules.contact.schemas import ContactPublic, ContactWrite
from app.modules.contact.service import ContactService
from app.modules.profiles.access import ProfileAccess
from app.modules.profiles.transport import reject_body
from app.shared.principal import Principal


def create_router(service: ContactService, access: ProfileAccess) -> APIRouter:
    router = APIRouter(prefix="/api/v1/profiles")

    @router.get("/me/contacts", dependencies=[Depends(access.owner), Depends(reject_body)])
    def own(principal: Annotated[Principal, Depends(access.owner)]) -> ContactWrite:
        return service.get_owner(principal.user_id)

    @router.put("/me/contacts")
    def replace(data: ContactWrite,
                principal: Annotated[Principal, Depends(access.owner)]) -> ContactWrite:
        return service.put(principal.user_id, data)

    @router.get("/{profile_id}/contacts",
                dependencies=[Depends(access.public), Depends(reject_body)])
    def public(profile_id: UUID, request: Request, response: Response) -> ContactPublic:
        return service.get_public(profile_id)

    return router
