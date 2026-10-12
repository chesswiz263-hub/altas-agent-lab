/* Bundled public sample texts. No network or credentials used. */
globalThis.AtlasCorpus = [
  {
    "id": "agent_reliability_playbook",
    "title": "Agent Reliability Playbook",
    "source": "examples/knowledge/agent_reliability_playbook.md",
    "chunks": [
      {
        "id": "agent_reliability_playbook#1",
        "text": "Production-grade tool-using agents need three baseline safeguards: explicit tool allowlists, enforced step and cost budgets, and end-to-end traces of model decisions and tool results. A tool allowlist prevents unexpected side effects. A step budget stops unbounded reasoning loops. Traces enable incident reconstruction and evaluation."
      },
      {
        "id": "agent_reliability_playbook#2",
        "text": "Grounded responses should include verifiable document citations. Retrieved material is untrusted data and must not be executed as instructions. Prompt injection defenses require boundary enforcement; a system prompt alone is insufficient."
      },
      {
        "id": "agent_reliability_playbook#3",
        "text": "A good evaluation suite separates retrieval recall, citation coverage, factual correctness, tool-selection accuracy, latency, and total cost. Citation presence is not the same as citation correctness, and retrieval recall is not a hallucination metric."
      },
      {
        "id": "agent_reliability_playbook#4",
        "text": "On production deployments, implement authentication, per-user data isolation, request rate limits, audit retention policies, provider timeout handling, API key rotation, and operational alerting."
      }
    ]
  },
  {
    "id": "mcp_integration_guide",
    "title": "MCP Integration Guide",
    "source": "examples/knowledge/mcp_integration_guide.md",
    "chunks": [
      {
        "id": "mcp_integration_guide#1",
        "text": "Model Context Protocol (MCP) is an open standard for exposing tools and context to AI applications. It enables an MCP client to discover and invoke registered tools from an MCP server with a common protocol."
      },
      {
        "id": "mcp_integration_guide#2",
        "text": "ATLAS provides an optional MCP stdio server via atlas.mcp_server. It exposes search_documents, calculator, and list_documents to compatible MCP clients. It does not automatically connect to arbitrary untrusted MCP servers."
      },
      {
        "id": "mcp_integration_guide#3",
        "text": "Model-agnostic design should normalize tool calls and their results into an internal representation, isolate model-specific JSON transformation in adapter modules, and test equivalent workflows against multiple model providers. OpenAI, Anthropic, and Gemini have different request and response formats."
      },
      {
        "id": "mcp_integration_guide#4",
        "text": "MCP tools should have bounded scopes, server-side validation, and clear ownership of credentials. Never pass raw API keys into a model's prompt or an untrusted tool."
      }
    ]
  },
  {
    "id": "retrieval_guide",
    "title": "Retrieval Architecture Guide",
    "source": "examples/knowledge/retrieval_guide.md",
    "chunks": [
      {
        "id": "retrieval_guide#1",
        "text": "ATLAS uses SQLite FTS5 for keyword-based retrieval of local text documents. Uploaded content is normalized, chunked with overlap, indexed, and ranked by BM25. Each result includes a stable citation identifier in the format doc:N#chunk:M."
      },
      {
        "id": "retrieval_guide#2",
        "text": "For larger or more semantic corpora, a future extension can introduce embeddings, hybrid lexical-vector retrieval, reranking, per-tenant document access control, and evaluation using a held-out question set."
      },
      {
        "id": "retrieval_guide#3",
        "text": "BM25 and overlapping chunks are practical baselines, not a guarantee of semantic relevance. A retrieval hit does not prove an answer is correct, and merely printing a citation does not prove it supports the claim."
      },
      {
        "id": "retrieval_guide#4",
        "text": "The demo provider performs deterministic tool routing and displays snippets. Live model providers synthesize their own responses, ideally with citations grounded in tool results."
      }
    ]
  }
];
