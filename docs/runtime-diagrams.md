# Runtime Diagrams

These diagrams show the current end-to-end runtime shape of SecureRAGPipeline in more detail than the top-level README figure.

## Architecture Overview

```mermaid
flowchart LR
    U[User]
    S[Streamlit UI<br/>src/ragagent/app/streamlit_app.py]
    UP[(uploads/*.pdf)]
    I[Inngest Dev Server<br/>:8288]
    A[FastAPI + Inngest Functions<br/>src/ragagent/app/inngest_app.py :8000]
    D[ragagent.ingestion<br/>PDF load/chunk + embeddings]
    Q[ragagent.storage.qdrant_store<br/>QdrantStorage]
    V[(Qdrant<br/>:6333)]
    O[(OpenAI API)]

    U -->|Upload PDF / Ask Question| S
    S -->|Save upload| UP
    S -->|Send rag/ingest_pdf<br/>or rag/query_pdf_ai| I
    I -->|Deliver event| A

    A -->|Ingest flow| D
    A -->|Query embedding| D
    D -->|Embeddings| O
    A -->|Upsert/search vectors| Q
    Q --> V

    A -->|Query flow: LLM answer with retrieved context| O
    A -->|Run output| I
    S -->|Poll run status| I
    I -->|Return run output| S
    S -->|Answer + sources| U
```

## Ingestion Sequence

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant S as Streamlit UI
    participant I as Inngest Dev Server
    participant A as FastAPI + Inngest Function
    participant D as ragagent.ingestion
    participant O as OpenAI API
    participant Q as Qdrant

    U->>S: Upload PDF
    S->>S: Save file to uploads/*.pdf
    S->>I: Send event rag/ingest_pdf\n(pdf_path, source_id)
    I->>A: Trigger rag_inngest_pdf
    A->>D: load_and_chunk_pdf(pdf_path)
    D-->>A: chunks
    A->>A: scan extracted text
    alt quarantine
        A-->>I: Function output {ingested: 0, scan_decision: quarantine}
    else allow or review
        A->>O: embed_texts(chunks)
        O-->>A: vectors
        A->>Q: upsert(ids, vectors, payloads + security metadata)
        Q-->>A: upsert complete
        A-->>I: Function output {ingested: N, scan_decision: allow|review}
    end
    I-->>S: Event accepted
    S-->>U: Show ingestion triggered
```

## Query Sequence

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
    S->>I: Send event rag/query_pdf_ai\n(question, top_k, source_id?, user_role)
    S->>I: Start polling runs for event_id
    I->>A: Trigger rag_query_pdf_ai
    A->>O: embed_texts([question])
    O-->>A: query vector
    A->>A: build retrieval policy context
    A->>Q: search(query_vector, top_k, policy filter)
    Q-->>A: retrieved chunks + metadata
    A->>A: safe context builder
    A->>O: LLM inference with filtered labeled context
    O-->>A: answer
    A->>A: output filter
    A-->>I: Function output {answer, sources, num_contexts}
    loop Poll until run complete
        S->>I: GET /events/{event_id}/runs
        I-->>S: Run status / output if complete
    end
    S-->>U: Display answer + sources
```
