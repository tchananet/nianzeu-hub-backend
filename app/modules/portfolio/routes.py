from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.modules.portfolio.access import PortfolioAccess
from app.modules.portfolio.publishing import PublishingService
from app.modules.portfolio.responses import ItemOwner, UploadTicket
from app.modules.portfolio.schemas import ItemCreate, UploadRequest, ValidateRequest
from app.modules.portfolio.service import PortfolioService
from app.modules.portfolio.uploads import UploadService
from app.modules.portfolio.validation import ValidationService
from app.modules.profiles.access import private_headers
from app.modules.profiles.transport import reject_body
from app.shared.dto import Page, Pagination
from app.shared.principal import Principal
from app.shared.query import pagination


def private_router(
    service: PortfolioService,
    uploads: UploadService,
    validation: ValidationService,
    publishing: PublishingService,
    access: PortfolioAccess,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/profiles/me")

    @router.post("/portfolio", status_code=201)
    def create(
        data: ItemCreate,
        response: Response,
        principal: Annotated[Principal, Depends(access.owner)],
    ) -> ItemOwner:
        item = service.create(principal.user_id, data)
        response.headers["Location"] = f"/api/v1/profiles/me/portfolio/{item.id}"
        return item

    @router.get("/portfolio", dependencies=[Depends(reject_body)])
    def collection(
        principal: Annotated[Principal, Depends(access.collection)],
        query: Annotated[Pagination, Depends(pagination)],
    ) -> Page[ItemOwner]:
        return service.list_owner(principal.user_id, query)

    @router.post("/portfolio/upload-url")
    def upload_url(
        data: UploadRequest, principal: Annotated[Principal, Depends(access.upload_url)]
    ) -> UploadTicket:
        return uploads.issue(principal.user_id, data)

    @router.get("/portfolio/{item_id}", dependencies=[Depends(reject_body)])
    def read(
        item_id: UUID, principal: Annotated[Principal, Depends(access.owner)]
    ) -> ItemOwner:
        return service.get_owner(principal.user_id, item_id)

    @router.post("/portfolio/{item_id}/validate")
    def validate(
        item_id: UUID,
        data: ValidateRequest,
        principal: Annotated[Principal, Depends(access.validate)],
    ) -> ItemOwner:
        return validation.validate(principal.user_id, item_id, data)

    @router.post("/portfolio/{item_id}/publish", dependencies=[Depends(reject_body)])
    def publish(
        item_id: UUID, principal: Annotated[Principal, Depends(access.owner)]
    ) -> ItemOwner:
        return publishing.publish(principal.user_id, item_id)

    @router.post("/portfolio/{item_id}/unpublish", dependencies=[Depends(reject_body)])
    def unpublish(
        item_id: UUID, principal: Annotated[Principal, Depends(access.owner)]
    ) -> ItemOwner:
        return publishing.unpublish(principal.user_id, item_id)

    @router.delete(
        "/portfolio/{item_id}",
        status_code=204,
        response_class=Response,
        dependencies=[Depends(reject_body)],
    )
    def remove(
        item_id: UUID, principal: Annotated[Principal, Depends(access.owner)]
    ) -> Response:
        service.delete(principal.user_id, item_id)
        response = Response(status_code=204)
        private_headers(response)
        return response

    return router
