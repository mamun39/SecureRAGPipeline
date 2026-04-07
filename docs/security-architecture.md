# Security Architecture

This document describes the current security-aware RAG flow implemented in this repository. It focuses on where controls are applied, what they do today, and what they do not do.

## Scope

The current implementation is an app-layer demo. It adds layered controls around:

- ingestion-time suspicious-content scanning
- quarantine enforcement before embeddings/upsert
- retrieval-time metadata filtering
- safe context construction before model invocation
- post-generation output screening
- structured security event logging

It does not provide strong identity, durable audit guarantees, sandboxed parsing, or robust data loss prevention.

## End-to-End Flow

### Ingestion

1. A PDF is uploaded through the Streamlit UI.
2. The file is saved under `uploads/`.
3. An Inngest event triggers the ingestion workflow.
4. The PDF is loaded and split into chunks.
5. Extracted text is scanned for suspicious phrases.
6. If the decision is `quarantine`, ingestion stops before embedding and Qdrant upsert.
7. Otherwise, chunk embeddings are created.
8. Chunks are written to Qdrant with security-aware metadata.

### Query

1. A user question is submitted through the Streamlit UI.
2. The query workflow embeds the question.
3. A demo retrieval policy context is built from the selected role.
4. Qdrant search runs with metadata-aware filtering.
5. Retrieved chunks are passed through a safe context builder.
6. The resulting context is sent to the LLM with an instruction to treat retrieved text as untrusted evidence.
7. The generated answer is screened by the output filter.
8. The screened answer and sources are returned.

## Control Layers

## 1. Ingestion Scanner

The ingestion scanner performs simple phrase-based detection over extracted document text.

Examples of flagged phrases:

- `ignore previous instructions`
- `reveal system prompt`
- `exfiltrate`
- `system prompt`
- `execute`

Output:

- `score`
- `flags`
- `decision` = `allow`, `review`, or `quarantine`

Current limitation:

- detection is heuristic and narrow
- it does not analyze parser exploits, embedded active content, or obfuscated attacks

## 2. Quarantine Enforcement

If the ingestion scanner returns `quarantine`:

- no embeddings are created
- no chunks are written to Qdrant
- the decision is logged and returned in the workflow result

Current limitation:

- there is no dedicated quarantine store or review workflow

## 3. Retrieval-Time Authorization

Retrieval uses metadata filters in Qdrant.

Current filter inputs:

- `tenant_id`
- `classification` allowlist
- `ingest_decision != quarantine`
- optional `source_id`

Current role mapping:

- `public` -> `public`
- `employee` -> `public`, `internal`
- `manager` -> `public`, `internal`, `confidential`
- `admin` -> `public`, `internal`, `confidential`, `restricted`

Current limitation:

- this is not real authentication
- role and tenant values are still demo-layer policy inputs

## 4. Safe Context Builder

Retrieved chunks are not passed directly to the model.

The safe context builder currently:

- drops quarantined chunks defensively
- drops review-marked chunks
- drops flagged chunks
- wraps kept chunks with metadata labels such as `source`, `classification`, and `trust`
- prepends an instruction telling the model to treat retrieved content as untrusted evidence

Current limitation:

- the behavior is conservative and heuristic
- it does not perform nuanced scoring, redaction, or per-chunk risk balancing

## 5. Output Filter

Generated answers are screened after model generation.

Current checks include:

- obvious API-key-like strings
- long restricted-looking content dumps
- simple email-like and phone-like patterns

Possible outcomes:

- `allow`
- `redact`
- `block`

Current limitation:

- this is not a complete guardrail system or DLP layer

## 6. Audit Logging

Structured local logs are emitted for:

- upload received
- ingestion scan result
- quarantine decision
- retrieval policy context used
- retrieved chunk summary
- output filter decision

Current limitation:

- logs are local process logs only
- they are not durable, tamper-evident, or externally aggregated

## Metadata Model

Chunk payloads currently support:

- `doc_id`
- `chunk_id`
- `tenant_id`
- `owner_id`
- `classification`
- `trust_level`
- `ingest_scan_flags`
- `ingest_decision`
- `content_hash`
- `created_at`

These fields support future policy evolution, but several values still use demo defaults today.

## Current Demo Defaults

- `tenant_id = "demo"`
- `owner_id = "local_user"`
- `classification = "internal"`
- `trust_level = "user_uploaded"`
- `ingest_scan_flags = []` unless the scanner flags content
- `ingest_decision = "allow"` unless the scanner overrides it

## Non-Goals

The current implementation does not claim to solve:

- real authentication or identity federation
- durable authorization policy management
- parser sandboxing
- malware scanning
- trusted document provenance
- formal prompt-injection resistance
- robust secret/PII exfiltration prevention
- tamper-evident auditability
