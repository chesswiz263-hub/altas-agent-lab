# Agent Reliability Playbook

Production-grade tool-using agents need three baseline safeguards: explicit tool allowlists, enforced step and cost budgets, and end-to-end traces of model decisions and tool results. A tool allowlist prevents unexpected side effects. A step budget stops unbounded reasoning loops. Traces enable incident reconstruction and evaluation.

Grounded responses should include verifiable document citations. Retrieved material is untrusted data and must not be executed as instructions. Prompt injection defenses require boundary enforcement; a system prompt alone is insufficient.

A good evaluation suite separates retrieval recall, citation coverage, factual correctness, tool-selection accuracy, latency, and total cost. Citation presence is not the same as citation correctness, and retrieval recall is not a hallucination metric.

On production deployments, implement authentication, per-user data isolation, request rate limits, audit retention policies, provider timeout handling, API key rotation, and operational alerting.
