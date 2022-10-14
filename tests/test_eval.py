from inspect import getmembers, isfunction
from textwrap import dedent
from typing import Any, Callable

import pytest

import randomjson.ast as ast
import randomjson.eval as eval
import randomjson.function as function


@pytest.mark.parametrize(
    "title,obj,want",
    [
        (
            "vanish elements from list",
            [1, 2, {"type": "randomjson.control.vanish"}, 3],
            [1, 2, 3],
        ),
        (
            "vanish elements from dict",
            {
                "k1": 1,
                "k2": 2,
                "k100": {"type": "randomjson.control.vanish"},
                "k3": 3,
            },
            {
                "k1": 1,
                "k2": 2,
                "k3": 3,
            },
        ),
        (
            "vanish elements",
            {
                "k1": {
                    "k11": {"type": "randomjson.control.vanish"},
                },
                "k2": {"type": "randomjson.control.vanish"},
                "k3": [
                    {"type": "randomjson.control.vanish"},
                    "a1",
                    {"type": "randomjson.control.vanish"},
                ],
            },
            {
                "k1": {},
                "k3": ["a1"],
            },
        ),
    ],
)
def test_vanisher(title: str, obj: Any, want: Any):
    assert want == eval.Vanisher.run(obj)


class FunctionSet:
    @staticmethod
    def five() -> int:
        return 5

    @staticmethod
    def add2(x: int) -> int:
        return x + 2

    @staticmethod
    def switch(x: int, rev: bool = True) -> int:
        return -x if rev else x

    @staticmethod
    def add(*args: tuple[int, ...]) -> int:
        return sum(args)


def gather_functions() -> dict[str, Callable]:
    return dict(getmembers(FunctionSet, isfunction))


class Counter:
    def __init__(self):
        self.__reg = 0

    def count(self) -> int:
        # with side effect
        self.__reg += 1
        return self.__reg


@pytest.mark.parametrize(
    "title,env,node,want,exc",
    [
        (
            "cond 2 hits but choose the first",
            eval.Environment.new(),
            ast.Cond(
                body=[
                    (
                        ast.Const(value=True),
                        ast.Const(value="hit"),
                    ),
                    (
                        ast.Const(value=True),
                        ast.Const(value="final"),
                    ),
                ]
            ),
            "hit",
            None,
        ),
        (
            "cond hit final",
            eval.Environment.new(),
            ast.Cond(
                body=[
                    (
                        ast.Const(value=False),
                        ast.Const(value="hit"),
                    ),
                    (
                        ast.Const(value=True),
                        ast.Const(value="final"),
                    ),
                ]
            ),
            "final",
            None,
        ),
        (
            "cond no hits",
            eval.Environment.new(),
            ast.Cond(
                body=[
                    (
                        ast.Const(value=False),
                        ast.Const(value="hit"),
                    ),
                ]
            ),
            eval.Vanisher.mark(),
            None,
        ),
        (
            "cond 1 case hit",
            eval.Environment.new(),
            ast.Cond(
                body=[
                    (
                        ast.Const(value=True),
                        ast.Const(value="hit"),
                    ),
                ]
            ),
            "hit",
            None,
        ),
        (
            "const",
            eval.Environment.new(),
            ast.Const(value=1),
            1,
            None,
        ),
        (
            "variable not found",
            eval.Environment.new(),
            ast.Variable(name="x"),
            None,
            eval.EvalError,
        ),
        (
            "variable",
            eval.Environment.new(
                variables=eval.VariableTable.new(
                    {
                        "x": 2,
                    }
                ),
            ),
            ast.Variable(name="x"),
            2,
            None,
        ),
        (
            "call five",
            eval.Environment.new(
                functions=eval.FunctionTable.new(gather_functions()),
            ),
            ast.Function.new(name="five"),
            5,
            None,
        ),
        (
            "call five with arguments",
            eval.Environment.new(
                functions=eval.FunctionTable.new(gather_functions()),
            ),
            ast.Function.new(name="five", args=[ast.Const(value=1)]),
            None,
            eval.EvalError,
        ),
        (
            "call add2",
            eval.Environment.new(
                functions=eval.FunctionTable.new(gather_functions()),
            ),
            ast.Function.new(name="add2", args=[ast.Const(value=5)]),
            7,
            None,
        ),
        (
            "call switch",
            eval.Environment.new(
                functions=eval.FunctionTable.new(gather_functions()),
            ),
            ast.Function.new(name="switch", args=[ast.Const(value=5)]),
            -5,
            None,
        ),
        (
            "call switch with keyword",
            eval.Environment.new(
                functions=eval.FunctionTable.new(gather_functions()),
            ),
            ast.Function.new(name="switch", args=[ast.Const(value=5)], kwargs={"rev": ast.Const(value=False)}),
            5,
            None,
        ),
        (
            "call add without arguments",
            eval.Environment.new(
                functions=eval.FunctionTable.new(gather_functions()),
            ),
            ast.Function.new(name="add"),
            0,
            None,
        ),
        (
            "call add with an argument",
            eval.Environment.new(
                functions=eval.FunctionTable.new(gather_functions()),
            ),
            ast.Function.new(name="add", args=[ast.Const(value=1)]),
            1,
            None,
        ),
        (
            "call add with arguments",
            eval.Environment.new(
                functions=eval.FunctionTable.new(gather_functions()),
            ),
            ast.Function.new(name="add", args=[ast.Const(value=1), ast.Const(value=2)]),
            3,
            None,
        ),
        (
            "call add with arguments and a variable",
            eval.Environment.new(
                functions=eval.FunctionTable.new(gather_functions()),
                variables=eval.VariableTable.new(
                    {
                        "x": 3,
                    }
                ),
            ),
            ast.Function.new(name="add", args=[ast.Const(value=1), ast.Const(value=2), ast.Variable(name="x")]),
            6,
            None,
        ),
        (
            "call add with a function as an argument",
            eval.Environment.new(
                functions=eval.FunctionTable.new(gather_functions()),
            ),
            ast.Function.new(
                name="add",
                args=[
                    ast.Const(value=1),
                    ast.Function.new(
                        name="add2",
                        args=[ast.Const(value=10)],
                    ),
                ],
            ),
            13,
            None,
        ),
        (
            "repeat dict",
            eval.Environment.new(),
            ast.Repeat(
                amount=ast.Const(value=2),
                node={
                    "k": ast.Const(value=1),
                },
            ),
            [
                {"k": 1},
                {"k": 1},
            ],
            None,
        ),
        (
            "repeat list",
            eval.Environment.new(),
            ast.Repeat(
                amount=ast.Const(value=2),
                node=[ast.Const(value=1)],
            ),
            [[1], [1]],
            None,
        ),
        (
            "repeat amount is not int",
            eval.Environment.new(),
            ast.Repeat(
                amount=ast.Const(value="x"),
                node=ast.Const(value=1),
            ),
            None,
            eval.EvalError,
        ),
        (
            "repeat zero",
            eval.Environment.new(),
            ast.Repeat(
                amount=ast.Const(value=0),
                node=ast.Const(value=100),
            ),
            [],
            None,
        ),
        (
            "repeat negative",
            eval.Environment.new(),
            ast.Repeat(
                amount=ast.Const(value=-1),
                node=ast.Const(value=100),
            ),
            [],
            None,
        ),
        (
            "repeat const",
            eval.Environment.new(),
            ast.Repeat(
                amount=ast.Const(value=3),
                node=ast.Const(value=100),
            ),
            [100, 100, 100],
            None,
        ),
        (
            "repeat function",
            eval.Environment.new(
                functions=eval.FunctionTable.new(
                    {
                        "count": Counter().count,
                    }
                ),
            ),
            ast.Repeat(
                amount=ast.Const(value=3),
                node=ast.Function.new(name="count"),
            ),
            [1, 2, 3],  # because count() has a side effect
            None,
        ),
    ],
)
def test_eval(title: str, env: eval.Environment, node: ast.Node, want: Any, exc: Exception | None):
    if exc:
        with pytest.raises(exc):
            eval.Evaluator(env).eval(node)
        return

    got = eval.Evaluator(env).eval(node)
    assert want == got


def test_function():
    stmts = [
        "c = 0",
        dedent(
            """\
        def cnt(d: int) -> int:
            global c
            c += d
            return c
        """
        ),
    ]
    got = function.Function.build(stmts)
    assert 1 == len(got)
    f = got[0]
    assert 1 == f(1)
    assert 3 == f(2)
    assert 3 == f(0)
