"""Policy and authorization context models."""

import pydantic

from ..config import DEFAULT_ALLOW_LOW_TRUST, DEFAULT_DEMO_TENANT_ID

class RetrievalPolicyContext(pydantic.BaseModel):
    """App-layer policy inputs for retrieval filtering."""

    tenant_id: str = DEFAULT_DEMO_TENANT_ID
    user_role: str = "user"
    allowed_classifications: list[str] = pydantic.Field(default_factory=lambda: ["internal"])
    allow_low_trust: bool = DEFAULT_ALLOW_LOW_TRUST
