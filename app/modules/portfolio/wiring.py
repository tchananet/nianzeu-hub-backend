from dataclasses import dataclass

from fastapi import APIRouter

from app.modules.portfolio.access import PortfolioAccess
from app.modules.portfolio.content import ContentService
from app.modules.portfolio.context import PortfolioContext
from app.modules.portfolio.public_routes import public_router
from app.modules.portfolio.publishing import PublishingService
from app.modules.portfolio.routes import private_router
from app.modules.portfolio.service import PortfolioService
from app.modules.portfolio.uploads import UploadService
from app.modules.portfolio.validation import ValidationService


@dataclass(frozen=True)
class PortfolioModule:
    """Assembly point consumed by X01; no router is registered here."""

    service: PortfolioService
    uploads: UploadService
    validation: ValidationService
    publishing: PublishingService
    content: ContentService

    def routers(self, access: PortfolioAccess) -> list[APIRouter]:
        return [
            private_router(
                self.service, self.uploads, self.validation, self.publishing, access
            ),
            public_router(self.service, self.content, access),
        ]


def build_module(context: PortfolioContext) -> PortfolioModule:
    return PortfolioModule(
        service=PortfolioService(context),
        uploads=UploadService(context),
        validation=ValidationService(context),
        publishing=PublishingService(context),
        content=ContentService(context),
    )
