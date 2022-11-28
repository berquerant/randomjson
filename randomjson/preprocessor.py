"""
Provides preprocessing.

Available macros:

  "{{const|value}}"
    is converted into

    {
      "type": "const",
      "value": value
    }

    the value is a string.

  "{{const|value|type}}"
    is converted into

    {
      "type": "const",
      "value": value
    }

    the type of the value is `type`.
    This tries to convert `value` to type `type` by the builtin function `cast(value, type)`.

  "{{variable|name}}"
    is converted into

    {
      "type": "variable",
      "name": name
    }

  ["{{function|name}}", ...]
    is converted into

    {
      "type": "function",
      "name": name,
      "args": ...
    }

  ["{{repeat}}", amount, node]
    is converted into

    {
      "type": "repeat",
      "amount": amount,
      "node": node
    }

  ["{{cond}}, [test, node], ...]
    is converted into

    {
      "type": "cond",
      "body": [
        [test, node],
        ...
      ]
    }
"""
import logging
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, TypeVar

from randomjson.function import Builtin


class PreprocessError(Exception):
    """Raised when preprocess failed."""


T = TypeVar("T", bound=Callable)


def preprocess(f: T) -> T:
    """Raise `PreprocessError` when some errors occur."""

    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logging.debug("[preprocessor] %s %s", args, kwargs)
        try:
            r = f(*args, **kwargs)
            logging.debug("[preprocessor] %s %s procesed %s", args, kwargs, r)
            return r
        except Exception as e:
            raise PreprocessError() from e

    return wrapper  # type: ignore


class InvalidTemplateError(Exception):
    """Raised when failed to construct a `Template`."""


@dataclass
class Template:
    """A string like `{{XXX|XXX|...}}`."""

    value: str

    @staticmethod
    def new(value: str) -> "Template":
        try:
            if value.startswith("{{") and value.endswith("}}"):
                return Template(value=value.lstrip("{{").rstrip("}}").lstrip().rstrip())
            raise Exception("not wrapped")
        except Exception as e:
            raise InvalidTemplateError(value) from e

    @property
    def tag(self) -> str:
        """The leftmost element."""
        return self.value.split("|", maxsplit=1)[0]

    @property
    def body(self) -> list[str]:
        """Elements except the leftmost element."""
        return self.value.split("|")[1:]


class Preprocessor:
    """Preprocessing runner."""

    @staticmethod
    def __process_str(value: str) -> Any:
        try:
            t = Template.new(value)
        except InvalidTemplateError as e:
            logging.debug("[preprocessor] ignore %s", e)
            return value

        match t.tag:
            case "const":
                match t.body:
                    case [val]:  # {{const|val}}
                        return {
                            "type": "const",
                            "value": val,
                        }
                    case [val, typ]:  # {{const|val|typ}} val as typ
                        try:
                            return {
                                "type": "const",
                                "value": Builtin.cast(val, typ),
                            }
                        except Exception as e:
                            logging.exception("[preprocessor] ignore invalid template for const %s %s", value, e)
                            return value
            case "variable":
                match t.body:
                    case [name]:  # {{variable|name}}
                        return {
                            "type": "variable",
                            "name": name,
                        }

        logging.warning("[preprocessor] ignore %s", value)
        return value

    def __process_list(self, value: list[Any]) -> Any:
        if not value:
            return []

        head, tail = value[0], value[1:]

        def shift():
            return [self.process(x) for x in value]

        try:
            t = Template.new(head)
        except InvalidTemplateError as e:
            logging.debug("[preprocessor] ignore %s in %s", e, value)
            return shift()

        match t.tag:
            case "cond":
                match t.body:
                    case []:  # ["{{cond}}, [test, node], ...]
                        try:
                            return {
                                "type": "cond",
                                "body": [[self.process(t), self.process(e)] for t, e in tail],
                            }
                        except Exception as e:
                            logging.exception("[preprocessor] ignore invalid template for cond %s %s", value, e)
            case "function":
                match t.body:
                    case [name]:  # ["{{function|name}}", ...]
                        try:
                            r: dict[str, Any] = {
                                "type": "function",
                                "name": name,
                            }
                            args = [self.process(x) for x in tail]
                            if args:
                                r["args"] = args
                            return r
                        except Exception as e:
                            logging.exception("[preprocessor] ignore invalid template for function %s %s", value, e)
            case "repeat":
                match t.body:
                    case []:
                        match tail:
                            case [amount, node]:  # ["{{repeat}}", amount, node]
                                try:
                                    return {
                                        "type": "repeat",
                                        "amount": self.process(amount),
                                        "node": self.process(node),
                                    }
                                except Exception as e:
                                    logging.exception(
                                        "[preprocessor] ignore invalid template for repeat %s %s", value, e
                                    )

        logging.warning("[preprocessor] ignore %s in %s", head, value)
        return shift()

    @preprocess
    def process(self, node: Any) -> Any:
        match node:
            case str():
                return self.__process_str(node)
            case list():
                return self.__process_list(node)
            case dict():
                return {k: self.process(v) for k, v in node.items()}
            case _:
                return node
