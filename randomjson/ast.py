"""Provides AST."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Self, TypeVar


class ParseError(Exception):
    """Raised when parse node error."""


ParserT = TypeVar("ParserT", bound=Callable)


def parser(f: ParserT) -> ParserT:
    """Raise `ParseError` when some exceptions occur."""

    @wraps(f)
    def wrapper(obj: Any) -> Any:
        logging.debug("[parser] %s", obj)
        try:
            r = f(obj)
            logging.debug("[parser] parse %s returned %s", obj, r)
            return r
        except Exception as e:
            raise ParseError(f"{obj}") from e

    return wrapper  # type: ignore


class InvalidNodeTypeError(Exception):
    """Raised when an object doesn't contain 'type'."""


def node_type(type_name: str) -> Callable[[ParserT], ParserT]:
    """Validate whether a given object has `type` and its value equals `type_name`."""

    def inner(f: ParserT) -> ParserT:
        @wraps(f)
        def wrapper(obj: Any) -> Any:
            try:
                if not isinstance(obj, dict):
                    raise Exception("not dict")
                typ = obj.get("type")
                if typ is None:
                    raise Exception("no type")
                if typ != type_name:
                    raise Exception(f"type mismatch, want {type_name} got {typ}")
            except Exception as e:
                raise InvalidNodeTypeError(f"want {type_name} from {obj}") from e
            return f(obj)

        return wrapper  # type: ignore

    return inner


class RequirePropertyError(Exception):
    """Raised when an object doesn't contain required keys."""


def node_properties(keys: list[str] | set[str] | str) -> Callable[[ParserT], ParserT]:
    """
    Validate whether a given object has some keys.

    :keys: required keys. e.g. ["key1", "key2"], {"key1", "key2"}, "key1 key2"
    """

    if isinstance(keys, list):
        keys = set(keys)
    if isinstance(keys, str):
        keys = set(keys.split())

    def inner(f: ParserT) -> ParserT:
        @wraps(f)
        def wrapper(obj: Any) -> Any:
            try:
                if not isinstance(obj, dict):
                    raise Exception("not dict")
                if set(obj.keys()) < keys:  # type: ignore
                    raise Exception("not enough keys")
            except Exception as e:
                raise RequirePropertyError(f"require {keys} for {obj}") from e
            return f(obj)

        return wrapper  # type: ignore

    return inner


class Node(ABC):
    @staticmethod
    @abstractmethod
    def parse(obj: Any) -> Self:  # type: ignore
        """Parse `obj` as `Node`."""

    @classmethod
    def select(cls, obj: Any) -> Self:  # type: ignore
        """Try to parse `obj` as some kind of `Node`."""

        excs: list[Exception] = []
        for ncls in cls.__subclasses__():
            logging.debug("[select] %s %s", ncls.__name__, obj)
            try:
                r = ncls.parse(obj)
                logging.debug("[select] %s %s returned %s", ncls.__name__, obj, r)
                return r
            except ParseError as e:
                excs.append(e)
        raise ParseError(f"`select` cannot parse {obj} {excs}")


TopLevelUnion = Node | list[Node] | dict[str, Node]


def parse_top_level_union(obj: Any) -> TopLevelUnion:
    if isinstance(obj, list):
        return [Node.select(x) for x in obj]
    try:
        return Node.select(obj)
    except Exception:
        return {k: Node.select(v) for k, v in obj.items()}


@dataclass
class Const(Node):
    """
    Constant.

    {
      "type": "const",
      "value": any
    }
    """

    value: Any

    @staticmethod
    @parser
    @node_properties("value")
    @node_type("const")
    def parse(obj: Any) -> Self:  # type: ignore
        return Const(value=obj["value"])


@dataclass
class Variable(Node):
    """
    Variable, accepts input from the external world.

    {
      "type": "variable",
      "name": str
    }
    """

    name: str

    @staticmethod
    @parser
    @node_properties("name")
    @node_type("variable")
    def parse(obj: Any) -> Self:  # type: ignore
        if not isinstance(obj["name"], str):
            raise Exception("want str for name")
        return Variable(name=obj["name"])


@dataclass
class Function(Node):
    """
    Function call.

    {
      "type": "function",
      "name": str,
      "args": list[Node],  // optional
      "kwargs: dict[str, Node]  // optional
    }
    """

    name: str
    args: list[Node]
    kwargs: dict[str, Node]

    @staticmethod
    def new(name: str, args: list[Node] | None = None, kwargs: dict[str, Any] | None = None) -> "Function":
        return Function(
            name=name,
            args=[] if args is None else args,
            kwargs={} if kwargs is None else kwargs,
        )

    @staticmethod
    @parser
    @node_properties("name")
    @node_type("function")
    def parse(obj: Any) -> Self:  # type: ignore
        name = obj["name"]
        args = obj.get("args", [])
        kwargs = obj.get("kwargs", {})
        if not isinstance(name, str):
            raise Exception("want str for name")
        if not isinstance(args, list):
            raise Exception("want list for args")
        if not (isinstance(kwargs, dict) and all(isinstance(x, str) for x in kwargs)):
            raise Exception("want dict[str, Any] for kwargs")
        return Function(
            name=name,
            args=[Node.select(x) for x in args],
            kwargs={k: Node.select(v) for k, v in kwargs.items()},
        )


@dataclass
class Repeat(Node):
    """
    Repeat the child.

    {
      "type": "repeat",
      "node": Node | dict[str, Node] | list[Node],
      "amount": Node  # eval as int
    }
    """

    node: TopLevelUnion
    amount: Node

    @staticmethod
    @parser
    @node_properties("node amount")
    @node_type("repeat")
    def parse(obj: Any) -> Self:  # type: ignore
        node = obj["node"]
        amount = obj["amount"]
        return Repeat(node=parse_top_level_union(node), amount=Node.select(amount))


@dataclass
class Cond(Node):
    """
    Condition switch.

    {
      "type": "cond",
      "body": [
        [test1, expr1],
        [test2, expr2],
        ...
      ]
    }

    testX: Node
    exprX: Node | list[Node] | dict[str, Node]
    """

    body: list[tuple[Node, TopLevelUnion]]

    @staticmethod
    @parser
    @node_properties("body")
    @node_type("cond")
    def parse(obj: Any) -> Self:  # type: ignore
        body = obj["body"]
        if not isinstance(body, list):
            raise Exception("want list")
        result: list[tuple[Node, TopLevelUnion]] = []
        for i, b in enumerate(body):
            try:
                if len(b) != 2:
                    raise Exception("want size 2 tuple")
                result.append(
                    (
                        Node.select(b[0]),
                        parse_top_level_union(b[1]),
                    )
                )
            except Exception as e:
                raise Exception(f"body[{i}] {b}") from e
        return Cond(body=result)
