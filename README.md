# RAGAgent

A small Retrieval-Augmented Generation (RAG) demo built with FastAPI, Inngest, Qdrant, OpenAI, and Streamlit.

The project supports two workflows:

1. Ingest a PDF by splitting it into chunks, embedding the chunks, and storing them in Qdrant.
2. Ask a question and answer it using the most relevant stored chunks.

## Credit

This project was inspired by and gives credit to [ProductionGradeRAGPythonApp](https://github.com/techwithtim/ProductionGradeRAGPythonApp).

## How It Works

The application is split into a few simple pieces:

- [main.py](/C:/Users/MRAka/PycharmProjects/RAGAgent/main.py): FastAPI app and Inngest functions.
- [data_loader.py](/C:/Users/MRAka/PycharmProjects/RAGAgent/data_loader.py): PDF loading, chunking, and embeddings.
- [vector_db.py](/C:/Users/MRAka/PycharmProjects/RAGAgent/vector_db.py): Qdrant wrapper for storing and searching vectors.
- [custom_types.py](/C:/Users/MRAka/PycharmProjects/RAGAgent/custom_types.py): Pydantic models used between steps.
- [streamlit_app.py](/C:/Users/MRAka/PycharmProjects/RAGAgent/streamlit_app.py): Simple UI for uploading PDFs and asking questions.

## Architecture

The backend is event-driven:

- FastAPI exposes the Inngest endpoint.
- Inngest listens for named events.
- When an event arrives, Inngest runs the matching function.

### Architecture Overview

```mermaid
flowchart LR
    U[User]
    S[Streamlit UI<br/>streamlit_app.py]
    UP[(uploads/*.pdf)]
    I[Inngest Dev Server<br/>:8288]
    A[FastAPI + Inngest Functions<br/>main.py :8000]
    D[data_loader.py<br/>PDF load/chunk + embeddings]
    Q[vector_db.py<br/>QdrantStorage]
    V[(Qdrant<br/>:6333)]
    O[(OpenAI API)]

    U -->|Upload PDF / Ask Question| S
    S -->|Save upload| UP
    S -->|Send rag/ingest_pdf<br/>or rag/query_pdf_ai| I
    I -->|Deliver event| A

    A -->|Ingest flow| D
    D -->|Embeddings| O
    A -->|Upsert/search vectors| Q
    Q --> V

    A -->|Query flow: LLM answer with retrieved context| O
    A -->|Run output| I
    I -->|Poll run status + output| S
    S -->|Answer + sources| U
```

### Ingestion Sequence

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant S as Streamlit UI
    participant I as Inngest Dev Server
    participant A as FastAPI + Inngest Function
    participant D as data_loader.py
    participant O as OpenAI API
    participant Q as Qdrant

    U->>S: Upload PDF
    S->>S: Save file to uploads/*.pdf
    S->>I: Send event rag/ingest_pdf\n(pdf_path, source_id)
    I->>A: Trigger rag_inngest_pdf
    A->>D: load_and_chunk_pdf(pdf_path)
    D-->>A: chunks
    A->>O: embed_texts(chunks)
    O-->>A: vectors
    A->>Q: upsert(ids, vectors, payloads)
    Q-->>A: upsert complete
    A-->>I: Function output {ingested: N}
    I-->>S: Run status/output available
    S-->>U: Show ingestion triggered/success
```

### Query Sequence

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant S as Streamlit UI
    participant I as Inngest Dev Server
    participant A as FastAPI + Inngest Function
    participant O as OpenAI API
    participant Q as Qdrant

    U->>S: Enter question (+ optional source filter)
    S->>I: Send event rag/query_pdf_ai\n(question, top_k, source_id?)
    I->>A: Trigger rag_query_pdf_ai
    A->>O: embed_texts([question])
    O-->>A: query vector
    A->>Q: search(query_vector, top_k, source_id?)
    Q-->>A: contexts + sources
    A->>O: LLM inference with retrieved context
    O-->>A: answer
    A-->>I: Function output {answer, sources, num_contexts}
    S->>I: Poll runs for event_id until complete
    I-->>S: Return run output
    S-->>U: Display answer + sources
```

The ingest flow is:

1. Receive a PDF event.
2. Read the PDF.
3. Split text into chunks.
4. Create embeddings for each chunk.
5. Store vectors plus metadata in Qdrant.

The query flow is:

1. Receive a question event.
2. Embed the question.
3. Search Qdrant for similar chunks.
4. Send the retrieved context to the LLM.
5. Return the answer and sources.

## Requirements

- Python 3.14+
- Qdrant running locally on `http://localhost:6333`
- OpenAI API key
- Inngest dev server for local development

## Environment Variables

Create a `.env` file in the project root with at least:

```env
OPENAI_API_KEY=your_openai_api_key
```

Optional:

```env
INNGEST_API_BASE=http://127.0.0.1:8288/v1
```

## Install Dependencies

If you are using `uv`:

```powershell
uv sync
```

If you are using a regular virtual environment:

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -e .
```

## Run The Project

You typically use three terminals.

### 1. Start Qdrant

Run Qdrant locally however you prefer, for example with Docker.

### 2. Start the FastAPI app

```powershell
.venv\Scripts\uvicorn main:app --reload
```

This starts the backend server, usually at `http://127.0.0.1:8000`.

### 3. Start the Inngest dev server

```powershell
npx --ignore-scripts=false inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest --no-discovery
```

The local Inngest UI is usually available at `http://127.0.0.1:8288`.

### 4. Start the Streamlit UI

```powershell
.venv\Scripts\streamlit run streamlit_app.py
```

## Using The App

In the Streamlit UI:

1. Upload a PDF.
2. Wait for ingestion to complete.
3. Ask a question about the PDF content.
4. Review the generated answer and returned sources.

## Manual Event Testing

You can also test the system by sending events directly through the Inngest dev UI or API.

Relevant event names in the backend:

- `rag/ingest_pdf`
- `rag/query_pdf_ai`

Example ingest event payload:

```json
{
  "pdf_path": "C:\\path\\to\\file.pdf",
  "source_id": "file.pdf"
}
```

Example query event payload:

```json
{
  "question": "What is this PDF about?",
  "top_k": 5
}
```

## Notes

- `.env`, `.venv`, local caches, and `qdrant_storage/` are ignored by Git through [.gitignore](/C:/Users/MRAka/PycharmProjects/RAGAgent/.gitignore).
- If a secret was committed before `.gitignore` was added, it must be removed from Git history separately.
