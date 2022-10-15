import json
from tempfile import NamedTemporaryFile
from typing import Any

import pytest

import randomjson.cli as cli


@pytest.fixture
def random_json() -> dict[str, Any]:
    return {
        "schema": {"items": ["{{repeat}}", "{{variable|n}}", ["{{function|rand}}", "{{function|rmax}}"]]},
        "variables": {
            "n": 3,
        },
        "statements": ["def rmax(): return 100"],
    }


@pytest.fixture
def random_json_argument() -> cli.Argument:
    return cli.Argument(
        schema={"items": ["{{repeat}}", "{{variable|n}}", ["{{function|rand}}", "{{function|rmax}}"]]},
        variables={"n": 3},
        statements=["def rmax(): return 100"],
    )


def test_new_argument_raw(random_json, random_json_argument):
    args = [json.dumps(random_json)]
    assert random_json_argument == cli.new_argument(cli.new_parser().parse_args(args))


def test_new_argument_file(random_json, random_json_argument):
    with NamedTemporaryFile("w+t") as f:
        print(json.dumps(random_json), file=f)
        f.seek(0)
        args = [f"@{f.name}"]
        assert random_json_argument == cli.new_argument(cli.new_parser().parse_args(args))
