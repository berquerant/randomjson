"""Provides builtin functions."""
import json
import logging
import operator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import reduce, wraps
from inspect import getmembers, isfunction, signature
from random import choices, randint, random, sample, uniform
from typing import Any, Callable, TypeVar
from uuid import uuid4


class FunctionCallError(Exception):
    """Raised when failed to call function."""


FunctionT = TypeVar("FunctionT", bound=Callable)


def function(f: FunctionT) -> FunctionT:
    """Raise `FunctionCallError` when some errors occur."""
    fname = f.__name__
    sig = signature(f)

    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        msg = f"{fname}{sig} with {args}, {kwargs}"
        try:
            r = f(*args, **kwargs)
            logging.debug("[function] %s returned %s", msg, r)
            return r
        except Exception as e:
            raise FunctionCallError(msg) from e

    return wrapper  # type: ignore


class Counters(dict[str, int | float]):
    """Set of counters."""

    def __missing__(self, key: str) -> int:
        return 0

    def count(self, delta: int | float = 1, key: str = "default") -> int | float:
        """Add `delta` to the counter of which key is `key`."""
        self[key] += delta
        return self[key]


class Builtin:
    """Set of buildin functions."""

    counters = Counters()

    @staticmethod
    @function
    def count(*args, **kwargs) -> int | float:
        """
        Add a number to a counter and return the value.

        First arg(delta): a number to be added, default is 1.
        Second arg(key): a key of counter, default is "default".
        """
        return Builtin.counters.count(*args, **kwargs)

    @staticmethod
    @function
    def add(*args) -> bool | int | float | str | list | tuple | set | frozenset | set | dict:
        """
        Add elements.

        Requires 1 element at least.

        bools: apply `or`
        int, float: sum
        str: concatenation
        list, tuple: concatenation
        set: union
        dict: update(overwrite) items by right dict
        """
        if not args:
            raise Exception("cannot add empty")

        a = args[0]
        if isinstance(a, bool):
            return any(args)
        if isinstance(a, (int, float)):
            return sum(args)
        if isinstance(a, str):
            return "".join(args)
        if isinstance(a, list):
            return sum(args, start=[])
        if isinstance(a, tuple):
            return sum(args, start=tuple())
        if isinstance(a, (set, frozenset, dict)):
            return reduce(operator.or_, args)

        raise Exception(f"cannot add {type(a)}, {args}")

    @staticmethod
    @function
    def sub(left: Any, right: Any) -> bool | int | float | set | frozenset:
        """
        Subtract right from left.

        bool: left && !right
        int, float: subtraction
        set: set difference
        """
        if isinstance(left, bool):
            return left and not right
        if isinstance(left, (int, float, set, frozenset)):
            return left - right

        raise Exception(f"cannot sub {type(left)}, {left} {right}")

    @staticmethod
    @function
    def mul(*args) -> bool | int | float | set | frozenset:
        """
        Multiply elements.

        Require 1 element at least.

        bool: apply `and`
        int, float: product
        set: intersection
        """
        if not args:
            raise Exception("cannot mul empty")

        a = args[0]
        if isinstance(a, bool):
            return all(args)
        if isinstance(a, (int, float)):
            return reduce(operator.mul, args)
        if isinstance(a, (set, frozenset)):
            return reduce(operator.and_, args)

        raise Exception(f"cannot mul {type(a)}, {args}")

    @staticmethod
    @function
    def div(left: Any, right: Any) -> Any:
        """Division."""
        return left / right

    @staticmethod
    @function
    def mod(left: Any, right: Any) -> Any:
        """Reminder."""
        return left % right

    @staticmethod
    @function
    def pow(left: Any, right: Any) -> Any:
        """Power."""
        return left**right

    @staticmethod
    @function
    def cast(val: Any, typ: str) -> Any:
        """Try to convert `val` to type `typ`."""
        match typ:
            case "str":
                return str(val)
            case "int":
                return int(val)
            case "float":
                return float(val)
            case "list":
                if isinstance(val, str):
                    val = json.loads(val)
                return list(val)
            case "tuple":
                return tuple(val)
            case "set":
                return set(val)
            case "dict":
                if isinstance(val, str):
                    val = json.loads(val)
                return dict(val)
            case "bool":
                return bool(val)
            case _:
                raise Exception(f"cannot cast {val} to {typ}")

    @staticmethod
    @function
    def neg(value: bool | int | float) -> bool | int | float:
        """
        Negation.

        bool: apply `not`
        int, float: reverse the sign
        """
        if isinstance(value, bool):
            return not value
        if isinstance(value, (int, float)):
            return -value
        raise Exception(f"cannot neg {value}")

    @staticmethod
    @function
    def format(fmt: str, *args, **kwargs) -> str:
        """Python `string.format()`."""
        return fmt.format(*args, **kwargs)

    @staticmethod
    @function
    def len(value: Any) -> int:
        """Python `len()`."""
        return len(value)

    @staticmethod
    @function
    def eq(*args) -> bool:
        """Equal."""
        if len(args) < 2:
            raise Exception("require 2 arguments to compare")
        return all(x == y for x, y in zip(args[: len(args) - 1], args[1:]))

    @staticmethod
    @function
    def ne(*args) -> bool:
        """Not equal."""
        if len(args) < 2:
            raise Exception("require 2 arguments to compare")
        return all(x != y for x, y in zip(args[: len(args) - 1], args[1:]))

    @staticmethod
    @function
    def gt(left: Any, right: Any) -> bool:
        """Greater than."""
        return left > right

    @staticmethod
    @function
    def ge(left: Any, right: Any) -> bool:
        """Greater than or equal."""
        return left >= right

    @staticmethod
    @function
    def lt(left: Any, right: Any) -> bool:
        """Less than."""
        return left < right

    @staticmethod
    @function
    def le(left: Any, right: Any) -> bool:
        """Less than or equal."""
        return left <= right

    @staticmethod
    @function
    def copy(value: Any, amount: int) -> list[Any]:
        """Generate a list of which element is a copy of `value`."""
        return [value for _ in range(amount)]

    @staticmethod
    @function
    def choice(population: Any, k: int = 1) -> list[Any]:
        """Choose k elements from population."""
        return choices(population=population, k=k)

    @staticmethod
    @function
    def sample(population: Any, k: int = 1) -> list[Any]:
        """Choose k unique elements from population."""
        return sample(population=population, k=k)

    @staticmethod
    @function
    def rand(*args) -> int | float:
        """
        Return a random number.

        no arguments: float from [0.0, 1.0)
        1 int argument: integer from [0, max]
        1 float argument: float from [0.0, max)
        2 int arguments: integer from [min, max]
        2 float arguments: float from [min, max]
        """
        if not args:
            return random()

        if len(args) > 2:
            raise Exception(f"rand {len(args)} arguments unsupported {args}")

        def ends() -> tuple[Any, Any]:
            if len(args) == 1:
                return 0, args[0]
            return args[0], args[1]

        a = args[0]
        if isinstance(a, float):
            return uniform(*ends())
        if isinstance(a, int):
            return randint(*ends())
        raise Exception(f"cannot generate rand from {type(a)} {ends()}")

    @staticmethod
    @function
    def uuid() -> str:
        """Return a new uuid4."""
        return str(uuid4())

    @classmethod
    def all_functions(cls) -> dict[str, Callable]:
        return dict(getmembers(cls, isfunction))


@dataclass
class SymTable:

    table: dict[str, Any]

    @contextmanager
    def apply(self):
        """Register symbols to global symtable."""
        updated_keys = set(self.table.keys()) & set(globals().keys())
        if updated_keys:
            raise Exception(f"cannot update global symtable keys {updated_keys}")
        added_keys = set(self.table.keys()) - set(globals().keys())
        for k, v in self.table.items():  # update global symtable
            globals()[k] = v
        yield
        for k in self.table:  # save modified values
            self.table[k] = globals()[k]
        for k in added_keys:  # revert global symtable
            del globals()[k]


@dataclass
class Function:
    """
    A function with local symtable.
    For functions from exec() or eval().
    """

    func: Callable
    symtable: SymTable
    code: str

    @property
    def name(self) -> str:
        return self.func.__name__

    def __call__(self, *args, **kwargs) -> Any:
        with self.symtable.apply():
            return self.func(*args, **kwargs)

    @staticmethod
    def build(stmts: list[str]) -> list["Function"]:
        """Compile statements and find functions."""
        table: dict[str, Any] = {}
        code_and_func: list[tuple[str, Callable]] = []

        for stmt in stmts:
            # execute statement and register function defined by it
            before = set(table.keys())
            exec(stmt, globals(), table)
            for k in set(table.keys()) - before:
                v = table[k]
                if isfunction(v):
                    logging.debug("[build function] %s %s", v, stmt)
                    code_and_func.append((stmt, v))

        symtable = SymTable(table=table)
        return [Function(func=function(func), symtable=symtable, code=code) for code, func in code_and_func]
