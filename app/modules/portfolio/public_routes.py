from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse

from app.modules.portfolio.access import PortfolioAccess
from app.modules.portfolio.content import ContentService
from app.modules.portfolio.responses import ItemPublic
from app.modules.portfolio.service import PortfolioService
from app.modules.profiles.transport import reject_body
from app.shared.dto import Page, Pagination
from app.shared.query import pagination


def public_router(
    service: PortfolioService, content: ContentService, access: PortfolioAccess
) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    @router.get(
        "/profiles/{profile_id}/portfolio",
        dependencies=[Depends(access.public), Depends(reject_body)],
    )
    def collection(
        profile_id: UUID, query: Annotated[Pagination, Depends(pagination)]
    ) -> Page[ItemPublic]:
        return service.list_public(profile_id, query)

    @router.get(
        "/portfolio/{item_id}/content",
        dependencies=[Depends(access.content), Depends(reject_body)],
        response_class=StreamingResponse,
    )
    def download(item_id: UUID) -> StreamingResponse:
        """Published items only; the bucket stays private and unlisted."""
        return content.stream(item_id)

    return router
