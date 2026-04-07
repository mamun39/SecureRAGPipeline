import importlib
import unittest


_SPLIT_TEST_MODULES = [
    "tests.integration.test_ingest_workflow",
    "tests.unit.test_ingestion_scanner",
    "tests.unit.test_output_filter",
    "tests.unit.test_retrieval_policy",
]


def load_tests(loader, _standard_tests, pattern):
    """Keep the legacy module runnable without duplicating discovery results."""
    if pattern is not None:
        return unittest.TestSuite()

    suite = unittest.TestSuite()
    for module_name in _SPLIT_TEST_MODULES:
        suite.addTests(loader.loadTestsFromModule(importlib.import_module(module_name)))
    return suite


if __name__ == "__main__":
    unittest.main()
