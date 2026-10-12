"""Strictly allowlisted, side-effect-free tools. No eval(), shell, or arbitrary URLs."""
import ast
import json
import math
import operator
from typing import Any

from atlas.embeddings import EmbeddingUnavailable
from atlas.store import Store


TOOL_SCHEMAS = [
    {
        "name": "search_documents",
        "description": "Search the local indexed knowledge base. Returns verifiable citation IDs and excerpts.",
        "parameters": {
            "type": "object", "properties": {
                "query": {"type": "string", "description": "Natural-language search terms"},
                "mode": {"type": "string", "enum": ["bm25", "hybrid", "semantic", "semantic_hybrid"]},
            }, "required": ["query"], "additionalProperties": False,
        },
    },
    {
        "name": "calculator",
        "description": "Safely evaluate basic numeric arithmetic (+ - * / % **). No Python code.",
        "parameters": {
            "type": "object", "properties": {
                "expression": {"type": "string", "description": "Arithmetic expression, e.g. (12+3)*2"},
            }, "required": ["expression"], "additionalProperties": False,
        },
    },
    {
        "name": "list_documents",
        "description": "List titles of documents available to the search tool.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]


_BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
           ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def safe_calculate(expression: str) -> float | int:
    if len(expression) > 140:
        raise ValueError("Expression too long")
    try:
        parsed = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError("Invalid arithmetic expression") from exc
    nodes = list(ast.walk(parsed))
    if len(nodes) > 35:
        raise ValueError("Expression too complex")

    def solve(node: ast.AST, depth: int = 0) -> float | int:
        if depth > 12:
            raise ValueError("Expression too deep")
        if isinstance(node, ast.Expression):
            return solve(node.body, depth + 1)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            if abs(node.value) > 1e12:
                raise ValueError("Number outside permitted range")
            return node.value
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            return _UNARY[type(node.op)](solve(node.operand, depth + 1))
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
            left, right = solve(node.left, depth + 1), solve(node.right, depth + 1)
            if isinstance(node.op, ast.Pow) and (abs(right) > 12 or abs(left) > 1e6):
                raise ValueError("Exponent exceeds safe limits")
            result = _BINARY[type(node.op)](left, right)
            if isinstance(result, complex) or not math.isfinite(result) or abs(result) > 1e15:
                raise ValueError("Result outside permitted range")
            return result
        raise ValueError("Unsupported syntax: only numeric arithmetic is permitted")

    try:
        return solve(parsed)
    except (ZeroDivisionError, OverflowError) as exc:
        raise ValueError("Arithmetic overflow or division by zero") from exc


def execute_tool(name: str, arguments: dict[str, Any], store: Store) -> str:
    if not isinstance(arguments, dict):
        return json.dumps({"error": "Tool arguments must be an object"})
    allowed: dict[str, set[str]] = {
        "search_documents": {"query", "mode"}, "calculator": {"expression"}, "list_documents": set(),
    }
    if name not in allowed:
        return json.dumps({"error": "Tool not allowlisted"})
    if set(arguments) - allowed[name]:
        return json.dumps({"error": "Unexpected tool argument"})
    try:
        if name == "search_documents":
            q = arguments.get("query", "")
            if not isinstance(q, str) or len(q) > 400 or not q.strip():
                raise ValueError("query must be a nonempty string of at most 400 characters")
            mode = arguments.get("mode", "bm25")
            if mode not in ("bm25", "hybrid", "semantic", "semantic_hybrid"):
                raise ValueError("Unknown retrieval mode")
            functions = {"bm25": store.search, "hybrid": store.search_hybrid,
                         "semantic": store.search_semantic,
                         "semantic_hybrid": store.search_semantic_hybrid}
            results = functions[mode](q, 5)
            return json.dumps({"results": results, "mode": mode}, ensure_ascii=False)
        if name == "calculator":
            expr = arguments.get("expression", "")
            if not isinstance(expr, str):
                raise ValueError("expression must be a string")
            return json.dumps({"result": safe_calculate(expr), "expression": expr})
        return json.dumps({"documents": store.list_documents()})
    except (ValueError, TypeError, EmbeddingUnavailable) as exc:
        return json.dumps({"error": str(exc)})
