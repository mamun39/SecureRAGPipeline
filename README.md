# SecureRAGPipeline

![Python](https://img.shields.io/badge/Python-3.14%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-app-009688?logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit&logoColor=white)
![Qdrant](https://img.shields.io/badge/Qdrant-vector%20store-DC244C)
![OpenAI](https://img.shields.io/badge/OpenAI-LLM-412991?logo=openai&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-security%20demo-orange)

A security-aware Retrieval-Augmented Generation (RAG) built with FastAPI, Inngest, Qdrant, OpenAI, and Streamlit.

It demonstrates layered app-level controls around ingestion, retrieval, prompt context assembly, output screening, and audit logging. It is an interactive security demo, not a hardened production boundary.

Further documentation:

- [Security Architecture](docs/security-architecture.md)
- [Runtime Diagrams](docs/runtime-diagrams.md)
- [Roadmap](docs/roadmap.md)

## Highlights

- ingestion scanning with `allow`, `review`, and `quarantine` decisions
- retrieval-time policy filtering by role and document metadata
- safe context construction that treats retrieved text as untrusted evidence
- output screening for obvious secret-like or sensitive patterns
- structured audit logging across the pipeline
- Streamlit UI for inspecting results, traces, documents, and audit events

The primary security-control figure lives in [Security Architecture](docs/security-architecture.md).

## What This Demonstrates

- PDF ingestion into a vector store
- ingestion-time suspicious-content scanning
- quarantine enforcement before embedding/upsert
- retrieval-time metadata filtering based on demo role policy
- safe prompt context construction from retrieved chunks
- post-generation output screening
- structured security event logging

## Quickstart

Requirements:

- Python 3.14+
- Qdrant running locally on `http://localhost:6333`
- OpenAI API key
- Inngest dev server for local development

Install:

```powershell
py -m venv .venv
.venv\Scripts\activate
.venv\Scripts\python.exe -m pip install -e .
```

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key
INNGEST_API_BASE=http://127.0.0.1:8288/v1
```

Run the app:

1. Start Qdrant locally.
2. Start the FastAPI/Inngest app:

```powershell
.venv\Scripts\uvicorn ragagent.app.inngest_app:app --reload
```

3. Start the Inngest dev server:

```powershell
npx --ignore-scripts=false inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest --no-discovery
```

4. Start Streamlit:

```powershell
.venv\Scripts\streamlit run src/ragagent/app/streamlit_app.py
```

## Testing

Preferred:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -t . -p "test_*.py"
```

## Project Structure

- [src/ragagent/app/](src/ragagent/app): entrypoints and UI
- [src/ragagent/workflows/](src/ragagent/workflows): ingest and query orchestration
- [src/ragagent/ingestion/](src/ragagent/ingestion): PDF loading and embeddings
- [src/ragagent/security/](src/ragagent/security): scanning, policy, filtering, and audit
- [src/ragagent/storage/](src/ragagent/storage): Qdrant access
- [src/ragagent/models/](src/ragagent/models): payload and result models
- [tests/](tests): unit and integration coverage

## Security Pipeline

| Stage | Current Control | Current Behavior | Current Limitation |
|---|---|---|---|
| Upload | Local file save + audit log | Uploaded PDFs are saved under `uploads/` and logged | No malware scanning or parser isolation |
| Ingestion scan | Phrase-based suspicious-content scan | Returns `score`, `flags`, and `allow` / `review` / `quarantine` | Can miss malicious content or over-flag benign text |
| Quarantine | Pre-embedding enforcement | `quarantine` documents are not embedded or stored in Qdrant | No separate review UI or durable quarantine store |
| Metadata | Security-aware chunk payloads | Chunks carry doc/chunk IDs, tenant, owner, classification, trust, decision, hash, timestamp | Most values still use demo defaults |
| Retrieval policy | App-layer metadata filter | Filters by tenant, classification allowlist, non-quarantine status, and optional source | No real authentication or server-trusted identity |
| Safe context | Context filtering + untrusted-text instruction | Quarantined and flagged/review chunks are excluded before prompt assembly | Heuristic and conservative rather than nuanced |
| Output filter | Simple answer screening | Blocks obvious secret-like output and restricted-looking dumps; redacts some simple sensitive patterns | Heuristic only; not robust DLP |
| Audit logging | Structured local logs | Logs upload, scan, quarantine, retrieval policy, retrieval summary, and output filter decisions | Local logs only; not durable or tamper-evident |

For more detail on control placement and current behavior, see [Security Architecture](docs/security-architecture.md).

## Demo Defaults

| Field | Default |
|---|---|
| `tenant_id` | `demo` |
| `owner_id` | `local_user` |
| `classification` | `internal` |
| `trust_level` | `user_uploaded` |
| `review` handling | still ingested |
| `quarantine` handling | blocked before embedding/upsert |

## Role Access Mapping

| Role | Allowed classifications |
|---|---|
| `public` | `public` |
| `employee` | `public`, `internal` |
| `manager` | `public`, `internal`, `confidential` |
| `admin` | `public`, `internal`, `confidential`, `restricted` |

## Try It

1. Upload a PDF and assign `classification` and `trust_level`.
2. Wait for ingestion to complete.
3. Ask the same question under different roles.
4. Inspect the answer summary, retrieval trace, document metadata, and audit events.

Detailed runtime diagrams live in [Runtime Diagrams](docs/runtime-diagrams.md). Lower-level control placement and security behavior are described in [Security Architecture](docs/security-architecture.md).

## Why This Project

- shows layered security controls across the full RAG lifecycle
- makes security behavior visible through an interactive UI
- provides a practical demo environment for experimentation and evaluation

## Troubleshooting

- `ImportError: attempted relative import with no known parent package`
  Ensure the project was installed with `pip install -e .` before using package-native commands.
- Streamlit starts but returns no answers
  Make sure the FastAPI app, Inngest dev server, and Qdrant are all running.
- `public` role returns no context
  New uploads default to `classification="internal"`, so `public` cannot retrieve them.
- Ingestion appears to succeed but document is not searchable
  Check whether the document was marked `quarantine` in logs.

## Limitations

The current system should be treated as a security-aware demo, not a hardened secure RAG platform.

- role selection in the UI is demo-only and not backed by real authentication
- tenant and owner metadata still use demo defaults, and classification/trust values are user-selected rather than trusted
- ingestion scanning is phrase-based and can miss malicious content or over-flag benign content
- safe context handling currently drops review-flagged chunks rather than applying nuanced risk scoring
- output filtering is heuristic and can miss secrets or over-block benign content
- the system does not isolate document parsing, sandbox model execution, or verify document provenance
- audit logs are local process logs and are not tamper-evident
- existing security layers reduce obvious risks, but none of them alone or together should be treated as a guarantee of safety

## Future Work

Future work includes real authentication, trusted server-side metadata, stronger ingestion controls, more nuanced context/output handling, durable audit storage, and broader evaluation coverage. The fuller phased plan lives in [Roadmap](docs/roadmap.md).

## Credit

This project was inspired by and gives credit to [ProductionGradeRAGPythonApp](https://github.com/techwithtim/ProductionGradeRAGPythonApp).

## License

This project is licensed under the [MIT License](LICENSE).

## Notes

- `.env`, `.venv`, local caches, and `qdrant_storage/` are ignored by Git through [.gitignore](.gitignore)
- if a secret was committed before `.gitignore` was added, it must be removed from Git history separately
