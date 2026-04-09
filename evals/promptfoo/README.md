# Promptfoo Eval Harness

This directory holds the baseline Promptfoo setup for exercising the local `POST /api/query` endpoint without using the Streamlit UI.

## Purpose

- provide a small, repeatable smoke test for the external query API
- provide a first indirect prompt-injection suite against the external query API
- establish the folder structure for future eval datasets, scenarios, and assertions
- keep the first eval step limited to harmless baseline checks

## Assumptions

- the FastAPI app is already running locally on `http://127.0.0.1:8000`
- the `POST /api/query` endpoint from Step 1 is available
- the local app is configured so it can answer a normal query

## Install Promptfoo

One option:

```powershell
npm install -g promptfoo
```

Or run it without a global install:

```powershell
npx promptfoo@latest --help
```

## Run The Smoke Eval

From the repository root:

```powershell
npx promptfoo@latest eval -c evals/promptfoo/promptfooconfig.yaml
```

## Run The Prompt-Injection Scenario

From the repository root:

```powershell
npx promptfoo@latest eval -c evals/promptfoo/scenarios/prompt_injection.yaml
```

## What The Baseline Covers

- sends a normal query to the local `POST /api/query` endpoint
- checks that the HTTP response is successful
- checks that the response body is valid JSON with the expected top-level fields
- checks that `answer` is non-empty

## Prompt-Injection Scenario

- sends indirect prompt-injection style questions framed as malicious retrieved content
- checks that the endpoint still returns valid JSON and a non-empty answer
- checks that the answer does not echo obvious override or leakage phrases such as `system prompt`, `ignore previous instructions`, `confidential marker`, `hidden metadata`, or `admin policy`

This step is intentionally small. Additional adversarial suites and broader security evals will be added in later steps.
