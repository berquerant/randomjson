"""Entry point of CLI."""
import argparse
import json
import logging
import random
from dataclasses import dataclass
from inspect import signature
from textwrap import dedent
from typing import Any, Callable, cast

from randomjson import preprocessor
from randomjson.ast import Node
from randomjson.eval import (
    Environment,
    Evaluator,
    FunctionTable,
    Vanisher,
    VariableTable,
)
from randomjson.function import Builtin, Function


@dataclass
class Argument:

    schema: dict[str, Any]
    variables: dict[str, Any]
    statements: list[str]

    @staticmethod
    def new(
        schema: dict[str, Any], variables: dict[str, Any] | None = None, statements: list[str] | None = None
    ) -> "Argument":
        return Argument(
            schema=schema,
            variables={} if variables is None else variables,
            statements=[] if statements is None else statements,
        )

    @classmethod
    def from_input_json(cls, value: dict[str, Any]) -> "Argument":
        return cls.new(**value)

    def into_input_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "variables": self.variables,
            "statements": self.statements,
        }

    def run_preprocessor(self) -> dict[str, Any]:
        return preprocessor.Preprocessor().process(self.schema)

    def parse_schema(self) -> dict[str, Node]:
        return {k: Node.select(v) for k, v in self.run_preprocessor().items()}

    def compile_statements(self) -> list[Function]:
        return Function.build(self.statements)

    def build_variable_table(self) -> VariableTable:
        return VariableTable.new(self.variables)

    def build_function_table(self) -> FunctionTable:
        return FunctionTable.new(Builtin.all_functions() | {x.name: x for x in self.compile_statements()})

    def build_environment(self) -> Environment:
        return Environment.new(
            variables=self.build_variable_table(),
            functions=self.build_function_table(),
        )

    def build_evaluator(self) -> Evaluator:
        return Evaluator(env=self.build_environment())

    def run(self) -> Any:
        evaluator = self.build_evaluator()
        result = {k: evaluator.eval(v) for k, v in self.parse_schema().items()}
        return Vanisher.run(result)


def generate_examples() -> str:
    def dumps(x: Any) -> str:
        return json.dumps(x, indent=4)

    def run_and_format(doc: str, a: Argument, only_preproces=False) -> str:
        input_json = dumps(a.into_input_json())
        result = dumps(a.run_preprocessor() if only_preproces else a.run())
        return f"{dedent(doc).lstrip()}\n{input_json}\n\nresult:\n\n{result}"

    examples: list[tuple[str, Argument, bool]] = [
        (
            """
            Random JSON schema:
            """,
            Argument.new(
                schema={
                    "random": {
                        "type": "function",
                        "name": "rand",
                    },
                },
            ),
            False,
        ),
        (
            """
            Repeat schema:
            """,
            Argument.new(
                schema={
                    "items": {
                        "type": "repeat",
                        "amount": {
                            "type": "const",
                            "value": 3,
                        },
                        "node": {
                            "type": "function",
                            "name": "rand",
                            "args": [
                                {
                                    "type": "const",
                                    "value": 100,
                                },
                            ],
                        },
                    },
                },
            ),
            False,
        ),
        (
            """
            Read variables:
            """,
            Argument.new(
                schema={
                    "items": {
                        "type": "repeat",
                        "amount": {
                            "type": "const",
                            "value": 3,
                        },
                        "node": {
                            "index": {
                                "type": "function",
                                "name": "count",
                            },
                            "rand": {
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
                variables={
                    "colors": [
                        "red",
                        "green",
                        "blue",
                    ],
                },
            ),
            False,
        ),
        (
            """
            Define fuctions:
            """,
            Argument.new(
                schema={
                    "items": {
                        "type": "repeat",
                        "amount": {
                            "type": "variable",
                            "name": "n",
                        },
                        "node": {
                            "datetime": {
                                "type": "function",
                                "name": "cast",
                                "args": [
                                    {
                                        "type": "function",
                                        "name": "add_hour",
                                        "args": [
                                            {
                                                "type": "variable",
                                                "name": "now",
                                            },
                                            {
                                                "type": "function",
                                                "name": "rand",
                                                "args": [
                                                    {
                                                        "type": "variable",
                                                        "name": "min",
                                                    },
                                                    {
                                                        "type": "variable",
                                                        "name": "max",
                                                    },
                                                ],
                                            },
                                        ],
                                    },
                                    {
                                        "type": "const",
                                        "value": "str",
                                    },
                                ],
                            },
                        },
                    },
                },
                variables={
                    "n": 3,
                    "now": "2022-10-13 11:00:00",
                    "min": -6,
                    "max": 6,
                },
                statements=[
                    "from datetime import datetime, timedelta",
                    dedent(
                        """\
                    def add_hour(now, delta):
                        return datetime.strptime(now, "%Y-%m-%d %H:%M:%S") + timedelta(hours=delta)
                    """
                    ),
                ],
            ),
            False,
        ),
        (
            """
            Use macros, only preprocessing:
            """,
            Argument.new(
                schema={
                    "title": "{{const|use macros}}",
                    "items": [
                        "{{repeat}}",
                        [
                            "{{function|rand}}",
                            "{{const|1|int}}",
                            "{{const|6|int}}",
                        ],
                        {
                            "id": [
                                "{{function|uuid}}",
                            ],
                            "index": [
                                "{{function|count}}",
                            ],
                            "color": [
                                "{{function|choice}}",
                                "{{variable|colors}}",
                            ],
                        },
                    ],
                },
            ),
            True,
        ),
        (
            """
            Use macros:
            """,
            Argument.new(
                schema={
                    "title": "{{const|use macros}}",
                    "items": [
                        "{{repeat}}",
                        [
                            "{{function|rand}}",
                            "{{const|1|int}}",
                            "{{const|6|int}}",
                        ],
                        {
                            "id": [
                                "{{function|uuid}}",
                            ],
                            "index": [
                                "{{function|count}}",
                            ],
                            "color": [
                                "{{function|choice}}",
                                "{{variable|colors}}",
                            ],
                        },
                    ],
                },
                variables={
                    "colors": [
                        "red",
                        "green",
                        "blue",
                    ],
                },
            ),
            False,
        ),
        (
            """
            Conditional branches:
            """,
            Argument.new(
                schema={
                    "items": [
                        "{{repeat}}",
                        "{{const|5|int}}",
                        {
                            "index": [
                                "{{function|count}}",
                            ],
                            "checked": [
                                "{{cond}}",
                                [
                                    [
                                        "{{function|eq}}",
                                        ["{{function|rand}}", "{{const|1|int}}"],
                                        "{{const|1|int}}",
                                    ],
                                    {
                                        "type": "const",
                                        "value": True,
                                    },
                                ],
                            ],
                        },
                    ],
                },
            ),
            False,
        ),
        (
            """
            Somewhat practical example:
            """,
            Argument.new(
                schema={
                    "items": [
                        "{{repeat}}",
                        "{{const|5|int}}",
                        {
                            "user_id": ["{{function|uuid}}"],
                            "action": ["{{function|choice}}", "{{variable|actions}}"],
                            "url": [
                                "{{function|add}}",
                                "{{const|https://sample}}",
                                ["{{function|cast}}", ["{{function|rand}}", "{{const|100|int}}"], "{{const|str}}"],
                                "{{const|.com}}",
                            ],
                            "ref": [
                                "{{cond}}",
                                [
                                    ["{{function|eq}}", ["{{function|rand}}", "{{const|1|int}}"], "{{const|1|int}}"],
                                    [
                                        "{{function|add}}",
                                        "{{const|https://sample}}",
                                        [
                                            "{{function|cast}}",
                                            ["{{function|rand}}", "{{const|100|int}}"],
                                            "{{const|str}}",
                                        ],
                                        "{{const|.com/ref}}",
                                    ],
                                ],
                            ],
                        },
                    ]
                },
                variables={
                    "actions": [
                        "pageview",
                        "click",
                        "conversion",
                    ],
                },
            ),
            False,
        ),
    ]

    return "Examples(--input-json):\n\n" + "\n\n".join(run_and_format(*x) for x in examples)


def generate_documents() -> str:
    ast_doc_title = "Available node types:"
    ast_doc = "".join(dedent(cast(str, x.__doc__)) for x in Node.__subclasses__())
    preprocessor_doc = cast(str, preprocessor.__doc__).lstrip()
    function_doc_title = "Available functions:\n"

    def format_function_doc(f: Callable) -> str:
        doc = "\n".join("  " + x for x in dedent(cast(str, f.__doc__)).lstrip().rstrip().split("\n"))
        return dedent(f"{f.__name__}{signature(f)}\n{doc}")

    function_doc = "\n\n".join(format_function_doc(f) for f in Builtin.all_functions().values())
    return "\n\n".join([ast_doc_title, ast_doc, preprocessor_doc, function_doc_title, function_doc])


def generate_epilog() -> str:
    return generate_documents() + "\n\n" + generate_examples()


def main() -> int:
    """Entry point of CLI."""
    parser = argparse.ArgumentParser(
        description="Generate random json.",
        epilog=generate_epilog(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input-json",
        type=str,
        action="store",
        help="JSON contains schema, variables and statements. If starts with '@' then the rest is filename.",
    )
    parser.add_argument(
        "-s",
        "--schema",
        type=str,
        action="store",
        help="Schema for random JSON. If starts with '@' then the rest is filename.",
    )
    parser.add_argument(
        "-t",
        "--variable",
        type=str,
        action="store",
        help="Variable table. If starts with '@' then the rest is filename.",
    )
    parser.add_argument("-i", "--statement", type=str, nargs="*", help="Statements for custom functions.")
    parser.add_argument("-E", "--only-preprocessor", action="store_true", help="Only run the preprocessor.")
    parser.add_argument("--seed", action="store", help="Seed of the random number generator.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging.")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    random.seed(args.seed)

    def value_or_file(key: str) -> str:
        if not key.startswith("@"):
            return key
        with open(key.lstrip("@")) as f:
            return f.read()

    def new_argument() -> Argument:
        if args.input_json:
            return Argument.from_input_json(json.loads(value_or_file(args.input_json)))

        return Argument.new(
            schema=json.loads(value_or_file(args.schema)),
            variables=json.loads(value_or_file(args.variable)),
            statements=args.statement,
        )

    def dump(x: Any):
        print(json.dumps(x, ensure_ascii=False, separators=(",", ":")))

    a = new_argument()
    if args.only_preprocessor:
        dump(a.run_preprocessor())
        return 0

    dump(a.run())
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
