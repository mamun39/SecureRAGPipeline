"""Helpers for building retrieval-time Qdrant filters from app-layer policy."""

from qdrant_client.models import Filter, FieldCondition, MatchAny, MatchValue

from ragagent.models.policy import RetrievalPolicyContext


LOW_TRUST_LEVELS = ["unverified", "low_trust"]
ROLE_CLASSIFICATION_ACCESS = {
    "public": ["public"],
    "employee": ["public", "internal"],
    "manager": ["public", "internal", "confidential"],
    "admin": ["public", "internal", "confidential", "restricted"],
}


def allowed_classifications_for_role(user_role: str) -> list[str]:
    """Return the demo classification allowlist for a role."""
    return ROLE_CLASSIFICATION_ACCESS.get(user_role, ROLE_CLASSIFICATION_ACCESS["public"])


def build_retrieval_filter(
    policy: RetrievalPolicyContext,
    source_id: str | None = None,
) -> Filter:
    """Build a Qdrant payload filter from a simple retrieval policy context."""
    must_conditions = [
        FieldCondition(
            key="tenant_id",
            match=MatchValue(value=policy.tenant_id),
        ),
        FieldCondition(
            key="classification",
            match=MatchAny(any=policy.allowed_classifications),
        ),
    ]

    must_not_conditions = [
        FieldCondition(
            key="ingest_decision",
            match=MatchValue(value="quarantine"),
        )
    ]

    if source_id:
        must_conditions.append(
            FieldCondition(
                key="source",
                match=MatchValue(value=source_id),
            )
        )

    if not policy.allow_low_trust:
        must_not_conditions.append(
            FieldCondition(
                key="trust_level",
                match=MatchAny(any=LOW_TRUST_LEVELS),
            )
        )

    return Filter(
        must=must_conditions,
        must_not=must_not_conditions,
    )
