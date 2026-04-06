import unittest

from custom_types import RetrievalPolicyContext
from security_retrieval_policy import allowed_classifications_for_role, build_retrieval_filter


class RetrievalPolicyTests(unittest.TestCase):
    def test_retrieval_policy_excludes_unauthorized_classifications(self):
        policy = RetrievalPolicyContext(
            tenant_id="demo",
            user_role="employee",
            allowed_classifications=["public", "internal"],
            allow_low_trust=False,
        )

        qdrant_filter = build_retrieval_filter(policy)
        classification_condition = next(
            condition for condition in qdrant_filter.must if condition.key == "classification"
        )

        self.assertEqual(classification_condition.match.any, ["public", "internal"])
        self.assertNotIn("confidential", classification_condition.match.any)

    def test_retrieval_policy_excludes_quarantined_docs(self):
        policy = RetrievalPolicyContext(
            tenant_id="demo",
            user_role="employee",
            allowed_classifications=["public", "internal"],
            allow_low_trust=False,
        )

        qdrant_filter = build_retrieval_filter(policy)
        ingest_decision_condition = next(
            condition for condition in qdrant_filter.must_not if condition.key == "ingest_decision"
        )

        self.assertEqual(ingest_decision_condition.match.value, "quarantine")

    def test_different_roles_yield_different_allowed_result_sets(self):
        public_allowed = allowed_classifications_for_role("public")
        manager_allowed = allowed_classifications_for_role("manager")

        self.assertEqual(public_allowed, ["public"])
        self.assertEqual(manager_allowed, ["public", "internal", "confidential"])
        self.assertNotEqual(public_allowed, manager_allowed)
