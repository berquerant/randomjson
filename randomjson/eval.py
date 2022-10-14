"""Provides ast evaluator."""
import logging
from dataclasses import dataclass
from functools import wraps
from inspect import signature
from typing import Any, Callable, TypeVar

from randomjson import ast


class EvalError(Exception):
    """Raised when an error occurs during eval."""


T = TypeVar("T", bound=Callable)


def evaluator(f: T) -> T:
    """Raise `EvalError` if some errors occur."""

    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logging.debug("[evaluator] %s %s", args, kwargs)
        try:
            r = f(*args, **kwargs)
            logging.debug("[evaluator] %s %s eval %s", args, kwargs, r)
            return r
        except Exception as e:
            raise EvalError() from e

    return wrapper  # type: ignore


class VariableTable:
    """Set of variables."""

    def __init__(self):
        self.__table: dict[str, Any] = {}

    @staticmethod
    def new(table: dict[str, Any]) -> "VariableTable":
        t = VariableTable()
        for k, v in table.items():
            t.set(k, v)
        return t

    def set(self, key: str, value: Any):
        self.__table[key] = value

    def get(self, key: str) -> Any:
        return self.__table.get(key)

    def has(self, key: str) -> bool:
        return key in self.__table


class FunctionTable:
    """Set of functions."""

    def __init__(self):
        self.__table: dict[str, Callable] = {}

    @staticmethod
    def new(table: dict[str, Callable]) -> "FunctionTable":
        t = FunctionTable()
        for k, v in table.items():
            t.set(k, v)
        return t

    def set(self, key: str, value: Callable):
        self.__table[key] = value

    def get(self, key: str) -> Callable | None:
        return self.__table.get(key)


@dataclass
class Environment:
    """Context to evaluate Node."""

    variables: VariableTable
    functions: FunctionTable

    @staticmethod
    def new(variables: VariableTable | None = None, functions: FunctionTable | None = None) -> "Environment":
        return Environment(
            variables=VariableTable() if variables is None else variables,
            functions=FunctionTable() if functions is None else functions,
        )


class Vanisher:
    @staticmethod
    def mark() -> Any:
        return {"type": "randomjson.control.vanish"}

    @classmethod
    def run(cls, obj: Any) -> Any:
        m = cls.mark()
        if isinstance(obj, list):
            return [cls.run(x) for x in obj if x != m]
        if isinstance(obj, dict):
            return {k: cls.run(v) for k, v in obj.items() if v != m}
        return obj


@dataclass
class Evaluator:
    env: Environment

    @staticmethod
    def __eval_const(node: ast.Const) -> Any:
        return node.value

    def __eval_variable(self, node: ast.Variable) -> Any:
        if not self.env.variables.has(node.name):
            raise Exception("variable {node.name} not found")
        return self.env.variables.get(node.name)

    def __eval_function(self, node: ast.Function) -> Any:
        f = self.env.functions.get(node.name)
        if f is None:
            raise Exception("function {node.name} not found")

        # evaluate arguments before call function
        args: list[Any] = []
        for i, x in enumerate(node.args):
            try:
                args.append(self.eval(x))
            except Exception as e:
                raise Exception(f"function {node.name} arg[{i}] {x}") from e

        kwargs: dict[str, Any] = {}
        for k, v in node.kwargs.items():
            try:
                kwargs[k] = self.eval(v)
            except Exception as e:
                raise Exception(f"function {node.name} kwargs[{k}] {v}") from e

        try:
            return f(*args, **kwargs)
        except Exception as e:
            raise Exception(f"function {node.name}{signature(f)} args {args} kwargs {kwargs} call") from e

    def __eval_top_level_union(self, node: ast.TopLevelUnion) -> Any:
        if isinstance(node, ast.Node):
            return self.eval(node)
        if isinstance(node, list):
            return [self.eval(x) for x in node]
        return {k: self.eval(v) for k, v in node.items()}

    def __eval_repeat(self, node: ast.Repeat) -> Any:
        try:
            count = self.eval(node.amount)
        except Exception as e:
            raise Exception("eval repeat amount") from e
        if not isinstance(count, int):
            raise Exception(f"repeat amount should be int but got {count}")

        result: list[Any] = []
        for i in range(count):
            try:
                result.append(self.__eval_top_level_union(node.node))
            except Exception as e:
                raise Exception(f"repeat [{i}/{count}]") from e
        return result

    def __eval_cond(self, node: ast.Cond) -> Any:
        if not node.body:
            return Vanisher.mark()

        for i, c in enumerate(node.body):
            try:
                if self.eval(c[0]):
                    logging.debug("[eval] cond[{i}] {c} is selected")
                    return self.__eval_top_level_union(c[1])
            except Exception as e:
                raise Exception(f"eval cond[{i}] {c}") from e

        logging.debug("[eval] cond %s not matched", node)
        return Vanisher.mark()

    @evaluator
    def eval(self, node: ast.Node) -> Any:
        """Evaluate node."""
        try:
            if isinstance(node, ast.Const):
                return self.__eval_const(node)
            if isinstance(node, ast.Variable):
                return self.__eval_variable(node)
            if isinstance(node, ast.Function):
                return self.__eval_function(node)
            if isinstance(node, ast.Repeat):
                return self.__eval_repeat(node)
            if isinstance(node, ast.Cond):
                return self.__eval_cond(node)
            raise Exception("Unknown node")
        except Exception as e:
            raise Exception(str(node)) from e
