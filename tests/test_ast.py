from typing import Any

import pytest

import randomjson.ast as ast


@pytest.mark.parametrize(
    "title,target,obj,want,exc",
    [
        (
            "const parse",
            ast.Const,
            {
                "type": "const",
                "value": 1,
            },
            ast.Const(value=1),
            None,
        ),
        (
            "const without type",
            ast.Const,
            {
                "value": 1,
            },
            None,
            ast.ParseError,
        ),
        (
            "const without value",
            ast.Const,
            {
                "type": "const",
            },
            None,
            ast.ParseError,
        ),
        (
            "const without dict",
            ast.Const,
            [1],
            None,
            ast.ParseError,
        ),
        (
            "parse function without arguments",
            ast.Function,
            {
                "type": "function",
                "name": "rand",
            },
            ast.Function.new(name="rand"),
            None,
        ),
        (
            "parse function with arguments",
            ast.Function,
            {
                "type": "function",
                "name": "add",
                "args": [
                    {
                        "type": "const",
                        "value": 1,
                    },
                    {
                        "type": "variable",
                        "name": "x",
                    },
                ],
                "kwargs": {
                    "v": {
                        "type": "const",
                        "value": 10,
                    },
                },
            },
            ast.Function.new(
                name="add",
                args=[
                    ast.Const(value=1),
                    ast.Variable(name="x"),
                ],
                kwargs={
                    "v": ast.Const(value=10),
                },
            ),
            None,
        ),
    ],
)
def test_parse(title: str, target: type, obj: Any, want: ast.Node | None, exc: Exception | None):
    if exc:
        with pytest.raises(exc):
            target.parse(obj)
        return

    assert want == target.parse(obj)
