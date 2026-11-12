from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from app.modules.profiles.access import ProfileAccess, private_headers
from app.modules.profiles.catalog import list_skills, parse_query
from app.modules.profiles.responses import ProfileOwner, ProfilePublic, SkillRead
from app.modules.profiles.schemas import ProfileWrite
from app.modules.profiles.service import ProfilesService
from app.modules.profiles.transport import reject_body
from app.modules.profiles.views import ViewsService
from app.shared.dto import Page
from app.shared.principal import Principal


def create_router(service: ProfilesService, views: ViewsService,
                  access: ProfileAccess) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    @router.get("/profiles/me", dependencies=[Depends(access.owner), Depends(reject_body)])
    def own(principal: Annotated[Principal, Depends(access.owner)]) -> ProfileOwner:
        return service.get_owner(principal.user_id)

    @router.put("/profiles/me")
    def put(data: ProfileWrite, response: Response,
            principal: Annotated[Principal, Depends(access.owner)]) -> ProfileOwner:
        value, created = service.put(principal.user_id, data)
        response.status_code = 201 if created else 200
        if created:
            response.headers["Location"] = f"/api/v1/profiles/{value.id}"
        return value

    @router.delete("/profiles/me", status_code=204, response_class=Response,
                   dependencies=[Depends(access.owner), Depends(reject_body)])
    def delete(principal: Annotated[Principal, Depends(access.owner)]) -> Response:
        service.delete(principal.user_id)
        response = Response(status_code=204)
        private_headers(response)
        return response

    @router.get("/profiles/{profile_id}",
                dependencies=[Depends(access.public), Depends(reject_body)])
    def public(profile_id: UUID, request: Request, response: Response) -> ProfilePublic:
        return service.get_public(profile_id)

    @router.post("/profiles/{profile_id}/views", status_code=204, response_class=Response,
                 dependencies=[Depends(access.view), Depends(reject_body)])
    def view(profile_id: UUID, visitor: Annotated[str, Depends(access.view)]) -> Response:
        response = Response(status_code=204)
        private_headers(response)
        views.record(profile_id, visitor)
        return response

    @router.get("/skills", dependencies=[Depends(access.public_limit), Depends(reject_body)])
    def skills(request: Request, response: Response) -> Page[SkillRead]:
        private_headers(response)
        return list_skills(service.factory, parse_query(request))

    return router
