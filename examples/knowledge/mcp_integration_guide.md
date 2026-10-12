# MCP Integration Guide

Model Context Protocol (MCP) is an open standard for exposing tools and context to AI applications. It enables an MCP client to discover and invoke registered tools from an MCP server with a common protocol.

ATLAS provides an optional MCP stdio server via atlas.mcp_server. It exposes search_documents, calculator, and list_documents to compatible MCP clients. It does not automatically connect to arbitrary untrusted MCP servers.

Model-agnostic design should normalize tool calls and their results into an internal representation, isolate model-specific JSON transformation in adapter modules, and test equivalent workflows against multiple model providers. OpenAI, Anthropic, and Gemini have different request and response formats.

MCP tools should have bounded scopes, server-side validation, and clear ownership of credentials. Never pass raw API keys into a model's prompt or an untrusted tool.
