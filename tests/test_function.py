from typing import Any, Callable

import pytest

import randomjson.function as function


def test_counters():
    counters = function.Counters()
    for kwargs, want in [
        ({}, 1),
        ({}, 2),
        ({"key": "k"}, 1),
        ({"key": "k", "delta": 2}, 3),
        ({"delta": 10}, 12),
        ({"key": "k", "delta": 0}, 3),
    ]:
        assert want == counters.count(**kwargs)


@pytest.mark.parametrize(
    "val,typ,want",
    [
        (12, "str", "12"),
        ("12", "int", 12),
        (12.5, "int", 12),
        ("12.5", "float", 12.5),
        ("[1,2,3]", "list", [1, 2, 3]),
        ([1, 2, 3], "tuple", (1, 2, 3)),
        ([1, 2, 3], "set", {1, 2, 3}),
        (1, "bool", True),
        (0, "bool", False),
        ('{"k": 10}', "dict", {"k": 10}),
    ],
)
def test_cast(val: Any, typ: str, want: Any):
    assert want == function.Builtin.cast(val, typ)


@pytest.mark.parametrize(
    "title,f,args,kwargs,want,exc",
    [
        (
            "add empty",
            function.Builtin.add,
            None,
            None,
            None,
            function.FunctionCallError,
        ),
        (
            "add bool false",
            function.Builtin.add,
            [False, False, False],
            None,
            False,
            None,
        ),
        (
            "add bool true",
            function.Builtin.add,
            [False, True],
            None,
            True,
            None,
        ),
        (
            "add dict",
            function.Builtin.add,
            [
                {
                    "k1": 1,
                    "k2": 2,
                },
                {
                    "k2": 10,
                    "k3": 3,
                },
            ],
            None,
            {
                "k1": 1,
                "k2": 10,
                "k3": 3,
            },
            None,
        ),
        (
            "add set",
            function.Builtin.add,
            [{1, 2}, {2, 3}],
            None,
            {1, 2, 3},
            None,
        ),
        (
            "add tuple",
            function.Builtin.add,
            [(1, 2), (3,)],
            None,
            (1, 2, 3),
            None,
        ),
        (
            "add list",
            function.Builtin.add,
            [[1, 2], [3]],
            None,
            [1, 2, 3],
            None,
        ),
        (
            "add string",
            function.Builtin.add,
            ["x", ",", "y"],
            None,
            "x,y",
            None,
        ),
        (
            "add number",
            function.Builtin.add,
            [1, 3],
            None,
            4,
            None,
        ),
        (
            "sub bool f-f",
            function.Builtin.sub,
            [False, False],
            None,
            False,
            None,
        ),
        (
            "sub bool f-t",
            function.Builtin.sub,
            [False, True],
            None,
            False,
            None,
        ),
        (
            "sub bool t-t",
            function.Builtin.sub,
            [True, True],
            None,
            False,
            None,
        ),
        (
            "sub bool t-f",
            function.Builtin.sub,
            [True, False],
            None,
            True,
            None,
        ),
        (
            "sub set",
            function.Builtin.sub,
            [{1, 2, 3}, {2}],
            None,
            {1, 3},
            None,
        ),
        (
            "sub number",
            function.Builtin.sub,
            [10, 3],
            None,
            7,
            None,
        ),
        (
            "mul empty",
            function.Builtin.mul,
            None,
            None,
            None,
            function.FunctionCallError,
        ),
        (
            "mul bool false",
            function.Builtin.mul,
            [True, False],
            None,
            False,
            None,
        ),
        (
            "mul bool true",
            function.Builtin.mul,
            [True, True, True],
            None,
            True,
            None,
        ),
        (
            "mul set",
            function.Builtin.mul,
            [{1, 2, 3}, {2, 3, 4}],
            None,
            {2, 3},
            None,
        ),
        (
            "mul number",
            function.Builtin.mul,
            [1, 2, 3, 4],
            None,
            24,
            None,
        ),
        (
            "div",
            function.Builtin.div,
            [14, 5],
            None,
            2.8,
            None,
        ),
        (
            "mod",
            function.Builtin.mod,
            [7, 3],
            None,
            1,
            None,
        ),
        (
            "pow",
            function.Builtin.pow,
            [2, 4],
            None,
            16,
            None,
        ),
        (
            "neg bool",
            function.Builtin.neg,
            [False],
            None,
            True,
            None,
        ),
        (
            "neg number",
            function.Builtin.neg,
            [10],
            None,
            -10,
            None,
        ),
        (
            "format",
            function.Builtin.format,
            ["format {} and {msg}", "message"],
            {
                "msg": "env",
            },
            "format message and env",
            None,
        ),
        (
            "len of str",
            function.Builtin.len,
            ["hello"],
            None,
            5,
            None,
        ),
        (
            "copy zero",
            function.Builtin.copy,
            [10, 0],
            None,
            [],
            None,
        ),
        (
            "copy negative",
            function.Builtin.copy,
            [10, -1],
            None,
            [],
            None,
        ),
        (
            "copy 3 times",
            function.Builtin.copy,
            [10, 3],
            None,
            [10, 10, 10],
            None,
        ),
    ],
)
def test_function(
    title: str,
    f: Callable,
    args: list[Any] | None,
    kwargs: dict[str, Any] | None,
    want: Any | None,
    exc: Exception | None,
):
    args = [] if args is None else args
    kwargs = {} if kwargs is None else kwargs
    if exc:
        with pytest.raises(exc):
            f(*args, **kwargs)
        return

    assert want == f(*args, **kwargs)
