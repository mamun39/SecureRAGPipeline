# Roadmap

This document outlines likely next steps beyond the current security-aware demo implementation.

## Near-Term

### Replace demo identity with trusted backend context

- provide `tenant_id`, `user_id`, and role/group claims from a real auth source
- remove trust in UI-submitted role values

Exit criteria:

- retrieval policy uses backend-provided identity context only

### Make document metadata explicit at ingest time

- require or derive `classification`, `owner_id`, `tenant_id`, and `trust_level`
- validate metadata before storage

Exit criteria:

- new documents are stored with meaningful policy metadata instead of defaults

### Improve ingestion screening

- add file validation and size/type limits
- expand suspicious-content heuristics
- produce clearer scan reason codes

Exit criteria:

- obvious hostile or malformed documents are handled more consistently before embedding

### Refine safe context assembly

- move beyond all-or-nothing dropping of review/flagged content
- support limited redaction or more nuanced chunk selection

Exit criteria:

- prompt context construction is explainable and less blunt

## Mid-Term

### Introduce real authorization policy evaluation

- make retrieval policy depend on authenticated tenant membership and trusted claims
- define clearer classification and trust rules

Exit criteria:

- different authenticated users see different retrieval results based on trusted policy inputs

### Add review workflows for flagged content

- support approval states for `review` documents/chunks
- define retrieval behavior for pending-review content

Exit criteria:

- flagged content is handled through explicit lifecycle states instead of ingest-only tagging

### Strengthen output controls

- separate secret leakage checks, restricted-content checks, and PII checks
- improve test coverage around output decisions

Exit criteria:

- output filtering has clearer categories and better regression coverage

### Improve auditability

- standardize event schemas
- add correlation IDs
- move logs to durable storage

Exit criteria:

- document and query lifecycles can be traced across ingest, retrieval, and output decisions

## Production-Readiness

### Harden trust boundaries

- isolate parsing, retrieval, and model interaction more clearly
- reduce blast radius of failures or compromised components

Exit criteria:

- the system has clearer operational and security boundaries

### Harden document handling

- use safer parser strategies
- add stronger validation and operational safeguards

Exit criteria:

- document ingestion is more resilient to malformed or hostile files

### Replace remaining demo assumptions

- remove hardcoded metadata defaults where authoritative values should exist
- manage classifications and policy centrally

Exit criteria:

- core security decisions rely on trusted data rather than development defaults

### Operationalize monitoring and incident response

- define alerts for quarantines, blocked outputs, and anomalous behavior
- retain logs and response procedures

Exit criteria:

- security-relevant events can drive investigation and response
