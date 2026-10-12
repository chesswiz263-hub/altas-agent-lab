import json

import pytest

from atlas.tools import execute_tool, safe_calculate


@pytest.mark.parametrize("expr,expected", [("(12+3)*2", 30), ("2 ** 5", 32), ("-3 + 5.5", 2.5), ("5%2", 1)])
def test_calculator(expr, expected):
    assert safe_calculate(expr) == expected


@pytest.mark.parametrize("expr", ["__import__('os').system('id')", "open('/etc/passwd')", "2 ** 99", "2/0", "[1,2]", "True", "2 << 5", "9" * 200])
def test_rejects_unsafe_math(expr):
    with pytest.raises(ValueError):
        safe_calculate(expr)


def test_tool_registry_rejects_arbitrary_functions(store):
    assert "not allowlisted" in execute_tool("shell_exec", {"command": "pwd"}, store)
    assert "Unexpected tool argument" in execute_tool("list_documents", {"command": "id"}, store)
    assert "error" in json.loads(execute_tool("calculator", {"expression": "x + 3"}, store))
