from typing import Any

import pytest

import randomjson.preprocessor as pp


@pytest.mark.parametrize(
    "title,node,want",
    [
        (
            "cond",
            ["{{cond}}", ["{{variable|f}}", "{{const|first}}"], ["{{variable|s}}", "{{const|second}}"]],
            {
                "type": "cond",
                "body": [
                    [{"type": "variable", "name": "f"}, {"type": "const", "value": "first"}],
                    [{"type": "variable", "name": "s"}, {"type": "const", "value": "second"}],
                ],
            },
        ),
        (
            "cond no cases",
            ["{{cond}}"],
            {
                "type": "cond",
                "body": [],
            },
        ),
        (
            "dict",
            {
                "items": [
                    "{{repeat}}",
                    ["{{function|rand}}", "{{const|1|int}}", "{{const|3|int}}"],
                    {
                        "id": ["{{function|uuid}}"],
                        "val": ["{{function|choice}}", "{{variable|colors}}"],
                    },
                ],
            },
            {
                "items": {
                    "type": "repeat",
                    "amount": {
                        "type": "function",
                        "name": "rand",
                        "args": [
                            {
                                "type": "const",
                                "value": 1,
                            },
                            {
                                "type": "const",
                                "value": 3,
                            },
                        ],
                    },
                    "node": {
                        "id": {
                            "type": "function",
                            "name": "uuid",
                        },
                        "val": {
                            "type": "function",
                            "name": "choice",
                            "args": [
                                {
                                    "type": "variable",
                                    "name": "colors",
                                },
                            ],
                        },
                    },
                },
            },
        ),
        (
            "ignore incomplete repeat",
            ["{{repeat}}"],
            ["{{repeat}}"],
        ),
        (
            "repeat with macro",
            ["{{repeat}}", "{{const|3|int}}", ["{{function|uuid}}"]],
            {
                "type": "repeat",
                "amount": {
                    "type": "const",
                    "value": 3,
                },
                "node": {
                    "type": "function",
                    "name": "uuid",
                },
            },
        ),
        (
            "repeat",
            ["{{repeat}}", {"type": "const", "value": 2}, {"type": "const", "value": "msg"}],
            {
                "type": "repeat",
                "amount": {
                    "type": "const",
                    "value": 2,
                },
                "node": {
                    "type": "const",
                    "value": "msg",
                },
            },
        ),
        (
            "const at the head of the list",
            ["{{const|top}}"],
            [
                {
                    "type": "const",
                    "value": "top",
                },
            ],
        ),
        (
            "function at the second element",
            [{"type": "const", "value": "top"}, ["{{function|uuid}}"]],
            [
                {
                    "type": "const",
                    "value": "top",
                },
                {
                    "type": "function",
                    "name": "uuid",
                },
            ],
        ),
        (
            "nested function with an argument",
            ["{{function|minus}}", "{{const|1|int}}", ["{{function|square}}", "{{const|4|int}}"]],
            {
                "type": "function",
                "name": "minus",
                "args": [
                    {
                        "type": "const",
                        "value": 1,
                    },
                    {
                        "type": "function",
                        "name": "square",
                        "args": [
                            {
                                "type": "const",
                                "value": 4,
                            },
                        ],
                    },
                ],
            },
        ),
        (
            "function with an argument",
            ["{{function|minus}}", {"type": "const", "value": 1}],
            {
                "type": "function",
                "name": "minus",
                "args": [
                    {
                        "type": "const",
                        "value": 1,
                    },
                ],
            },
        ),
        (
            "function without arguments",
            ["{{function|uuid}}"],
            {
                "type": "function",
                "name": "uuid",
            },
        ),
        (
            "ignore empty list",
            [],
            [],
        ),
        (
            "const failed to cast",
            "{{const|142|unknown}}",
            "{{const|142|unknown}}",
        ),
        (
            "const as int",
            "{{const|142|int}}",
            {
                "type": "const",
                "value": 142,
            },
        ),
        (
            "const",
            "{{const|142}}",
            {
                "type": "const",
                "value": "142",
            },
        ),
        (
            "variable",
            "{{variable|x}}",
            {
                "type": "variable",
                "name": "x",
            },
        ),
        (
            "ignore str template",
            "{{unknown}}",
            "{{unknown}}",
        ),
        (
            "ignore str",
            "string",
            "string",
        ),
    ],
)
def test_process(title: str, node: Any, want: Any):
    assert want == pp.Preprocessor().process(node)
