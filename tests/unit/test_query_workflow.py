import unittest
from unittest.mock import AsyncMock, patch

from secureragpipeline.models.payloads import RetrievedChunk
from secureragpipeline.models.results import ChunkTraceEntry, RAGSearchResult
from secureragpipeline.workflows import query_pdf


class QueryWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_execute_query_abstains_for_explicit_disallowed_classification_request(self):
        search_result = RAGSearchResult(
            contexts=["internal context"],
            sources=["test.pdf"],
            chunks=[
                RetrievedChunk(
                    text="internal context",
                    source="test.pdf",
                    classification="internal",
                )
            ],
        )
        safe_trace = [
            ChunkTraceEntry(
                source="test.pdf",
                classification="internal",
                text_preview="internal context",
            )
        ]
        generate_answer = AsyncMock()

        with patch.object(query_pdf, "_search", return_value=search_result), patch.object(
            query_pdf,
            "build_safe_context",
            return_value=("internal context", search_result.chunks, safe_trace, []),
        ):
            result = await query_pdf.execute_query(
                question="What confidential planning details are stored in the documents?",
                user_role="employee",
                tenant_id="demo",
                generate_answer=generate_answer,
            )

        self.assertEqual(result.answer, query_pdf.SAFE_REFUSAL_MESSAGE)
        self.assertEqual(result.output_filter_decision, "redact")
        self.assertIn("requested_classification_not_allowed", result.output_filter_reasons)
        generate_answer.assert_not_awaited()

    async def test_execute_query_allows_generation_for_allowed_classification_request(self):
        search_result = RAGSearchResult(
            contexts=["internal context"],
            sources=["test.pdf"],
            chunks=[
                RetrievedChunk(
                    text="internal context",
                    source="test.pdf",
                    classification="internal",
                )
            ],
        )
        safe_trace = [
            ChunkTraceEntry(
                source="test.pdf",
                classification="internal",
                text_preview="internal context",
            )
        ]
        generate_answer = AsyncMock(
            return_value={"choices": [{"message": {"content": "Internal guidance summary."}}]}
        )

        with patch.object(query_pdf, "_search", return_value=search_result), patch.object(
            query_pdf,
            "build_safe_context",
            return_value=("internal context", search_result.chunks, safe_trace, []),
        ):
            result = await query_pdf.execute_query(
                question="Summarize the internal guidance available to an employee.",
                user_role="employee",
                tenant_id="demo",
                generate_answer=generate_answer,
            )

        self.assertEqual(result.answer, "Internal guidance summary.")
        self.assertEqual(result.output_filter_decision, "allow")
        generate_answer.assert_awaited_once()
