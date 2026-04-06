"""PDF loading and chunking helpers."""

from llama_index.core.node_parser import SentenceSplitter
from llama_index.readers.file import PDFReader

from ragagent.config import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE


splitter = SentenceSplitter(chunk_size=DEFAULT_CHUNK_SIZE, chunk_overlap=DEFAULT_CHUNK_OVERLAP)


def load_and_chunk_pdf(path: str):
    """Read a PDF file and split its text into smaller chunks."""
    docs = PDFReader().load_data(file=path)
    texts = [d.text for d in docs if getattr(d, "text", None)]
    chunks = []
    for text in texts:
        chunks.extend(splitter.split_text(text))
    return chunks
