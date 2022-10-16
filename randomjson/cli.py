"""Entry point of CLI."""
import argparse
import json
import logging
import os
import random
import sys
from dataclasses import asdict, dataclass, field
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
    variables: dict[str, Any] = field(default_factory=dict)
    statements: list[str] = field(default_factory=list)
    only_preprocessor: bool = False

    @staticmethod
    def from_dict(value: dict[str, Any]) -> "Argument":
        return Argument(**value)

    def into_dict(self) -> dict[str, Any]:
        return asdict(self)

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
        if self.only_preprocessor:
            return self.run_preprocessor()
        evaluator = self.build_evaluator()
        result = {k: evaluator.eval(v) for k, v in self.parse_schema().items()}
        return Vanisher.run(result)


def generate_examples() -> str:
    def dumps(x: Any) -> str:
        return json.dumps(x, indent=4)

    def run_and_format(doc: str, a: Argument) -> str:
        input_json = dumps(a.into_dict())
        result = dumps(a.run())
        return f"{dedent(doc).lstrip()}\n{input_json}\n\nresult:\n\n{result}"

    examples: list[tuple[str, Argument]] = [
        (
            """
            Random JSON schema:
            """,
            Argument(
                schema={
                    "random": {
                        "type": "function",
                        "name": "rand",
                    },
                },
            ),
        ),
        (
            """
            Repeat schema:
            """,
            Argument(
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
        ),
        (
            """
            Read variables:
            """,
            Argument(
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
        ),
        (
            """
            Define fuctions:
            """,
            Argument(
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
        ),
        (
            """
            Use macros, only preprocessing:
            """,
            Argument(
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
                only_preprocessor=True,
            ),
        ),
        (
            """
            Use macros:
            """,
            Argument(
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
        ),
        (
            """
            Conditional branches:
            """,
            Argument(
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
        ),
        (
            """
            Somewhat practical example:
            """,
            Argument(
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
        ),
    ]

    return "EXAMPLES:\n\n" + "\n\n".join(run_and_format(*x) for x in examples)


def generate_documents() -> str:
    env_docs = {
        "RANDOMJSON_RANDOM_SEED": "Initialize the random number generator by this value if this is set.",
        "RANDOMJSON_VERBOSE": "Enable verbose logging if this is set.",
    }

    def format_env_doc(name: str, doc: str) -> str:
        doc = "\n".join("    " + x for x in dedent(doc).lstrip().rstrip().split("\n"))
        return f"  {name}:\n{doc}"

    env_doc = "ENVIRONMENT VARIABLES:\n\n" + "\n\n".join(
        format_env_doc(k, env_docs[k]) for k in sorted(env_docs.keys())
    )

    all_node_classes = Node.__subclasses__()
    ast_doc = "NODE TYPES:\n\n" + "".join(
        dedent(cast(str, x.__doc__)) for x in sorted(all_node_classes, key=lambda x: x.__name__)
    )

    preprocessor_doc = cast(str, preprocessor.__doc__).lstrip()

    def format_function_doc(f: Callable) -> str:
        doc = "\n".join("  " + x for x in dedent(cast(str, f.__doc__)).lstrip().rstrip().split("\n"))
        return dedent(f"{f.__name__}{signature(f)}\n{doc}")

    all_functions = Builtin.all_functions()
    function_doc = "FUNCTIONS:\n\n" + "\n\n".join(
        format_function_doc(all_functions[k]) for k in sorted(all_functions.keys())
    )

    return "\n\n".join([env_doc, ast_doc, preprocessor_doc, function_doc])


def generate_epilog() -> str:
    return generate_documents() + "\n\n" + generate_examples()


def __value_or_file_or_stdin(key: str) -> str:
    if not key.startswith("@"):
        return key
    if key == "@-":
        return sys.stdin.read()
    with open(key.lstrip("@")) as f:
        return f.read()


def new_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate random json.",
        epilog=generate_epilog(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "random_json",
        type=str,
        nargs=1,
        help=dedent(
            """\
        JSON contains schema, variables and statements.
        If starts with '@' then the rest is filename. '@-' to read stdin."""
        ),
    )
    parser.add_argument("-E", "--only-preprocessor", action="store_true", help="Only run the preprocessor.")

    return parser


def new_argument(args: argparse.Namespace) -> Argument:
    return Argument.from_dict(
        json.loads(__value_or_file_or_stdin(args.random_json[0])) | {"only_preprocessor": args.only_preprocessor}
    )


def main() -> int:
    """Entry point of CLI."""

    if "RANDOMJSON_VERBOSE" in os.environ:
        logging.basicConfig(level=logging.DEBUG)
    random.seed(os.environ.get("RANDOMJSON_RANDOM_SEED"))

    arg = new_argument(new_parser().parse_args())
    logging.debug("[randomjson] start run")
    print(json.dumps(arg.run(), ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
