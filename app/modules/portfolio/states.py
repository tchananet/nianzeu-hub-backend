from typing import Final

DRAFT: Final = "draft"
PENDING: Final = "pending"
VALIDATING: Final = "validating"
REJECTED: Final = "rejected"
VALIDATED: Final = "validated"
PUBLISHED: Final = "published"

ALL: Final = (DRAFT, PENDING, VALIDATING, REJECTED, VALIDATED, PUBLISHED)
UPLOADABLE: Final = (DRAFT, REJECTED)
FINAL_FILE: Final = (VALIDATED, PUBLISHED)

ITEM_QUOTA: Final = 20
BYTE_QUOTA: Final = 200 * 1048576
UPLOAD_TTL_SECONDS: Final = 300
LEASE_SECONDS: Final = 60
