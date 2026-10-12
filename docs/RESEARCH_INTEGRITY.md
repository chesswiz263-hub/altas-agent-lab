# ATLAS v1.0 — Research integrity contract

## Scientific research goal

Target long-term prompt: “Analyze the evidence for dark matter, evaluate competing theories, identify mathematical inconsistencies, and produce a research report with verified citations.”

This release is a **foundation for** that task, **not a solution to** that task. The public interface knows only its three AI engineering documents; it should abstain on dark-matter requests. The private `/api/research/dossier` endpoint searches only operator-ingested local materials; no external article fetch is performed.

## What a status means

- **INSUFFICIENT_EVIDENCE:** no passage met a bounded lexical coverage gate. It is not proof that no evidence exists.
- **EXCERPTS_AVAILABLE:** some local indexed text met a lexical relevance gate. The excerpts are not necessarily scientifically true or logically supportive.
- **Exact quote + digest:** checks that the returned text was extracted from a local indexed passage at report creation time. A hash does **not** validate an article's author, publication, DOI, retraction status, or external correctness.
- **NOT_EVALUATED hypothesis:** no comparative theoretical conclusion is made, even if an excerpt was retrieved.
- **EQUAL / NOT_EQUAL arithmetic:** exact rational arithmetic of numbers with +,-,*,/ and parentheses. Does not establish symbolic identities, unit consistency, parameter constraints, model predictions, or physical validity.
- **NOT_CHECKED arithmetic:** unsupported or invalid expression, including symbolic variables and arbitrary code.

## Planned research-quality milestones (not included)

1. Curated literature ingestion with stable DOI/arXiv metadata, publisher URLs, timestamps, license and source-chain provenance.
2. Independent citation and quote verification against downloaded primary documents, with retraction and revision awareness.
3. Scientific claim extraction and premise-conclusion linking, distinguishing empirical observation, model assumption, prediction, and inference.
4. Multi-hypothesis comparison of ΛCDM, MOND, and other models using attributed source evidence and documented counter-evidence.
5. Symbolic algebra, dimensional consistency, reproducible numeric notebooks, and uncertainty propagation with human-reviewed scientific assumptions.
6. Held-out physics research evaluations, adversarial source contamination tests, and subject-matter expert audits.

## Threat model

Public GitHub Pages demo is offline JavaScript with no live credentials. The Python API is intended for a trusted operator and should remain access-controlled. Documents are untrusted inputs. Do not treat citations, similarities, or LLM confidence scores as proof of truth; do not silently call external services.
