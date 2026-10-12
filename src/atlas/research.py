"""Bounded, source-traceable research dossier. No fabricated scientific synthesis."""
import ast
import hashlib
import re
from fractions import Fraction

STOP = set("a an and are as at be by can could do does for from have how in into is it its of on or should the their them these this to using was were what when where which who why with would about all".split())


def terms(value: str) -> set[str]:
    return {x for x in re.findall(r"[a-z0-9]+", value.casefold()) if len(x) > 1 and x not in STOP}


def _rational_expr(expression: str) -> Fraction:
    if len(expression) > 160:
        raise ValueError("Expression too long")
    def visit(node, depth=0):
        if depth > 16:
            raise ValueError("Expression too deep")
        if isinstance(node, ast.Expression):
            return visit(node.body, depth + 1)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return Fraction(str(node.value))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            operand = visit(node.operand, depth + 1)
            return -operand if isinstance(node.op, ast.USub) else operand
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            a, b = visit(node.left, depth + 1), visit(node.right, depth + 1)
            if isinstance(node.op, ast.Add): return a + b
            if isinstance(node.op, ast.Sub): return a - b
            if isinstance(node.op, ast.Mult): return a * b
            if b == 0: raise ValueError("Division by zero")
            return a / b
        raise ValueError("Only numeric +, -, *, / and parentheses are supported")
    try:
        result = visit(ast.parse(expression.strip(), mode='eval'))
    except (SyntaxError, TypeError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError("Invalid arithmetic expression") from exc
    if result.numerator.bit_length() > 1024 or result.denominator.bit_length() > 1024:
        raise ValueError("Arithmetic value too large")
    return result


def check_arithmetic(equations: list[str]) -> list[dict]:
    """Exact rational arithmetic only, not physical theory or symbolic algebra."""
    output = []
    for equation in equations:
        if equation.count('=') != 1:
            output.append({'equation': equation, 'status': 'NOT_CHECKED', 'reason': 'Expected exactly one equals sign'})
            continue
        left, right = equation.split('=', 1)
        try:
            lhs, rhs = _rational_expr(left), _rational_expr(right)
            output.append({'equation': equation, 'status': 'EQUAL' if lhs == rhs else 'NOT_EQUAL',
                           'left': str(lhs), 'right': str(rhs), 'scope': 'Exact rational arithmetic only'})
        except ValueError as exc:
            output.append({'equation': equation, 'status': 'NOT_CHECKED', 'reason': str(exc)})
    return output


def create_dossier(question: str, store, hypotheses: list[str] | None = None,
                   equations: list[str] | None = None) -> dict:
    """Searches stored documents; abstains when query-specific evidence is absent."""
    hypotheses = hypotheses or []
    equations = equations or []
    q = terms(question)
    results = store.search(question, limit=10)
    # No universal relevance score is treated as proof of entailment.
    ranked = []
    for row in results:
        matched = sorted(q & terms(row['body'] + ' ' + row['title']))
        if len(matched) < (1 if len(q) <= 1 else 2):
            continue
        coverage = len(matched) / len(q) if q else 0
        if coverage < (0.5 if len(q) <= 2 else 0.46):
            continue
        ranked.append((coverage, row, matched))
    ranked.sort(key=lambda entry: (-entry[0], entry[1]['chunk_id']))
    citations = []
    for score, item, matches in ranked[:5]:
        body = item['body']
        citations.append({'id': item['citation'], 'title': item['title'], 'quote': body,
                          'sha256': hashlib.sha256(body.encode('utf-8')).hexdigest(),
                          'exact_excerpt_from_index': True, 'query_coverage': round(score, 3),
                          'matched_terms': matches})
    return {
        'question': question, 'status': 'EXCERPTS_AVAILABLE' if citations else 'INSUFFICIENT_EVIDENCE',
        'citations': citations, 'hypotheses': [{'name': name, 'status': 'NOT_EVALUATED',
          'reason': 'Source retrieval alone cannot establish comparative scientific merit'} for name in hypotheses],
        'math_checks': check_arithmetic(equations),
        'limitations': ['Citations identify indexed local source excerpts, not externally authenticated literature.',
           'Lexical overlap does not establish semantic entailment or factual correctness.',
           'Arithmetic checks do not validate physical assumptions, symbolic derivations, or dimensional consistency.',
           'No autonomous web research or independent hypothesis comparison was performed.']
    }
