import unittest

from tests.integration.test_ingest_workflow import IngestWorkflowTests
from tests.unit.test_ingestion_scanner import IngestionScannerTests
from tests.unit.test_output_filter import OutputFilterTests
from tests.unit.test_retrieval_policy import RetrievalPolicyTests


class SecurityPipelineTests(
    IngestionScannerTests,
    IngestWorkflowTests,
    RetrievalPolicyTests,
    OutputFilterTests,
):
    pass


if __name__ == "__main__":
    unittest.main()
