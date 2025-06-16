from collections.abc import Iterable
from dataclasses import dataclass
from typing import (
    Any,
    Generic,
    TypeVar,
    Callable,
    Union,
    overload,
)

from typing_extensions import TypeVarTuple, Unpack

Ts = TypeVarTuple("Ts")
T = TypeVar("T", covariant=True)


def tap(*side_effects: Any, ret: T = None) -> T:
    """
    Utility function to perform side effects while returning a value.

    Useful for writing multiple side effects in a single lambda.

    >>> tap(print("Hello"), print("World"), ret=42)
    Hello
    World
    42
    >>> add_and_print = lambda a, b: tap(print(f"{a} + {b} = {a + b}"), ret=a + b)
    >>> add_and_print(1, 2)
    1 + 2 = 3
    3
    """
    return ret


@dataclass(frozen=True)
class apply(Generic[T]):
    """
    A class to apply a function to an argument.

    >>> nums = []
    >>> _ = apply(nums.append)(lambda: 1)  # This will append 1 to nums
    >>> nums
    [1]

    >>> _ = apply(nums.append).foreach(lambda: [2, 3, 4])  # This will append 2, 3, and 4 to nums
    >>> nums
    [1, 2, 3, 4]

    >>> _ = apply.unpack_to(print)(lambda: (1, 2, 3))
    1 2 3

    >>> _ = apply.unpack_to(print).foreach(lambda: [(1, 2), (3, 4), (5, 6)])
    1 2
    3 4
    5 6
    """

    func: Callable[[T], Any]

    def __call__(self, factory: Callable[[], T]) -> Callable[[], T]:
        result = factory()
        self.func(result)
        return lambda: result

    @staticmethod
    def unpack_to(func: Callable[[Unpack[Ts]], Any]) -> "apply[tuple[Unpack[Ts]]]":
        """
        Create an apply instance that unpacks the result of the factory function to the given function.

        >>> _ = apply.unpack_to(print)(lambda: (1, 2, 3))
        1 2 3

        unpack_to can also be used with foreach to apply the function to each item in an iterable:

        >>> _ = apply.unpack_to(print).foreach(lambda: [(1, 2), (3, 4), (5, 6)])
        1 2
        3 4
        5 6
        """
        return apply(lambda args: func(*args))

    def foreach(self, factory: Callable[[], Iterable[T]]) -> Callable[[], Iterable[T]]:
        """
        Create an apply instance that applies the function to each item in the iterable.

        >>> _ = apply(print).foreach(lambda: [1, 2, 3])
        1
        2
        3
        """
        results = factory()
        for r in results:
            self.func(r)
        return lambda: results


CaseT = TypeVar("CaseT")


def throw(e: Exception, /):
    """
    Create a function that raises the given exception when called.
    """
    raise e


@dataclass(frozen=True)
class Case(Generic[T]):
    condition: bool | Any
    factory: Callable[[], T]


@dataclass(frozen=True)
class _CaseBuilder:
    condition: bool | Any

    def __rshift__(self, factory: Callable[[], T]) -> Case[T]:
        """
        Create a case with the given condition and factory.
        """
        return Case(self.condition, factory)


def case(condition: bool | Any) -> _CaseBuilder:
    return _CaseBuilder(condition)


class UnexpectedCase(Exception):
    """
    Exception raised when no case matches in a switch expression.
    """


DefaultT = TypeVar("DefaultT")


@dataclass(frozen=True)
class switch(Generic[T]):
    """
    A simple switch expression that evaluates cases based on a value.

    Useful when you want match-case like functionality inside a lambda with an expression.

    Use `switch(var)[...]` when no unhandled case is expected

    >>> number = 2
    >>> switch(number)[
    ...     case(number < 0) >> (lambda: "Negative"),
    ...     case(number == 0) >> (lambda: "Zero"),
    ...     case(number > 0) >> (lambda: "Positive"),
    ... ]
    'Positive'

    Unexpected case will raise an UnexpectedCase exception:

    >>> number = 0
    >>> switch(number)[
    ...     case(number < 0) >> (lambda: "Negative"),
    ...     case(number > 0) >> (lambda: "Positive"),
    ... ]
    Traceback (most recent call last):
    ...
    dsl.UnexpectedCase: No matching case found for value: 0

    You can also use `switch(var)(...)` when unhandled case can fall back to a default value or factory:

    >>> number = -1
    >>> switch(number)(
    ...     case(number == 0) >> (lambda: "Zero"),
    ...     case(number > 0) >> (lambda: "Positive"),
    ...     default="Negative",
    ... )
    'Negative'

    >>> switch(number)(
    ...     case(number == 0) >> (lambda: "Zero"),
    ...     case(number > 0) >> (lambda: "Positive"),
    ...     default_factory=(lambda: "Negative"),
    ... )
    'Negative'
    """

    value: T

    @overload
    def __call__(
        self, *cases: Case[CaseT], default: DefaultT = None
    ) -> Union[CaseT, DefaultT]: ...

    @overload
    def __call__(
        self, *cases: Case[CaseT], default_factory: Callable[[T], DefaultT]
    ) -> Union[CaseT, DefaultT]: ...

    def __call__(self, *cases, **kwargs):
        for c in cases:
            if c.condition:
                return c.factory()
        if default := kwargs.get("default"):
            return default
        if default_factory := kwargs.get("default_factory"):
            return default_factory()

    def __getitem__(self, cases: tuple[Case[CaseT], ...]) -> CaseT:
        """
        Ensure that all cases are handled, raising an error if not.
        """
        for c in cases:
            if c.condition:
                return c.factory()
        raise UnexpectedCase(f"No matching case found for value: {self.value!r}")


R = TypeVar("R", covariant=True)
Es = TypeVarTuple("Es")


class catcher(Generic[T, Unpack[Es]]):
    def __init__(
        self,
        fn: Callable[[], T],
        *es: Unpack[Es],
    ) -> None:
        self.es: tuple[Unpack[Es]] = es
        self.fn = fn

    def fallback(self, value: R) -> "catcher[T | R, Unpack[Es]]":
        """
        Fallback to a value if an exception is raised.

        >>> catcher(lambda: 1 / 0, ZeroDivisionError).fallback(-1).unwrap()
        -1
        >>> catcher(lambda: 1 / 0, ZeroDivisionError).fallback("Error").unwrap()
        'Error'
        """

        def fn() -> T | R:
            try:
                return self.fn()
            except self.es:
                return value

        return catcher(fn, *self.es)

    def recover(
        self, exc: type[Exception], handler: Callable[[Exception], R]
    ) -> "catcher[T | R, Unpack[Es]]":
        """
        Recover from a specific exception type by applying a handler function.
        >>> catcher(lambda: 1 / 0, ZeroDivisionError).recover(ZeroDivisionError, lambda e: -1).unwrap()
        -1
        >>> catcher(lambda: 1 / 0, ZeroDivisionError).recover(ZeroDivisionError, lambda e: "Error").unwrap()
        'Error'
        """

        def fn() -> T | R:
            try:
                return self.fn()
            except exc as e:
                return handler(e)

        return catcher(fn, *self.es)

    def cleanup(self, fn: Callable[[], Any]) -> "catcher[T, Unpack[Es]]":
        """
        Run a cleanup function after the main function, regardless of success or failure.

        >>> catcher(lambda: 1 / 0, ZeroDivisionError).cleanup(lambda: print("Cleanup")).recover(ZeroDivisionError, lambda e: -1).unwrap()
        Cleanup
        -1
        """

        def wrapper() -> T:
            try:
                return self.fn()
            finally:
                fn()

        return catcher(wrapper, *self.es)

    def unwrap(self) -> T:
        """
        Unwrap the result of the function, raising any uncaught exceptions.

        >>> catcher(lambda: 1 / 0, ZeroDivisionError).unwrap()
        Traceback (most recent call last):
        ...
        ZeroDivisionError: division by zero
        >>> catcher(lambda: 1, ZeroDivisionError).unwrap()
        1
        """
        return self.fn()


class attempt(Generic[T]):
    """
    Utility class for simple exception handling with a single expression.

    Useful for doing simple error handling in lambda functions

    Usage example:
    >>> attempt(lambda: 1 / 0)()
    Traceback (most recent call last):
    ...
    ZeroDivisionError: division by zero

    >>> attempt(lambda: 1).map(str).map(lambda x: x + " is a number").unwrap()
    '1 is a number'
    >>> attempt(lambda: 1 / 0).catch(ZeroDivisionError).fallback(-1).unwrap()
    -1
    >>> attempt(lambda: 1 / 0).catch(ZeroDivisionError).recover(ZeroDivisionError, lambda e: -1).unwrap()
    -1
    >>> attempt(lambda: 1 / 0).catch(ZeroDivisionError).cleanup(lambda: print("Cleanup")).fallback("Error").unwrap()
    Cleanup
    'Error'
    """

    def __init__(self, fn: Callable[[], T]) -> None:
        self.fn = fn

    def unwrap(self) -> T:
        """
        Unwrap the result of the function, raising any uncaught exceptions.

        >>> attempt(lambda: 1 / 0).unwrap()
        Traceback (most recent call last):
        ...
        ZeroDivisionError: division by zero
        """
        return self.fn()

    def __call__(self) -> T:
        """
        Shorthand for calling the function and unwrapping the result.

        >>> attempt(lambda: 1 / 0)()
        Traceback (most recent call last):
        ...
        ZeroDivisionError: division by zero
        """
        return self.unwrap()

    def catch(self, *es: Unpack[Es]) -> "catcher[T, Unpack[Es]]":
        """
        Create a catcher instance to handle exceptions raised by the function.

        >>> attempt(lambda: 1 / 0).catch(ZeroDivisionError).unwrap()
        Traceback (most recent call last):
        ...
        ZeroDivisionError: division by zero
        >>> attempt(lambda: 1 / 0).catch(ZeroDivisionError).fallback(-1).unwrap()
        -1
        >>> attempt(lambda: 1 / 0).catch(ZeroDivisionError).recover(ZeroDivisionError, lambda e: -1).unwrap()
        -1
        >>> attempt(lambda: 1 / 0).catch(ZeroDivisionError).recover(ZeroDivisionError, lambda e: -1).cleanup(lambda: print("Cleanup")).unwrap()
        Cleanup
        -1
        """
        return catcher(self.fn, *es)

    def map(self, fn: Callable[[T], R]) -> "attempt[R]":
        """
        Map the result of the function to a new value using the provided function.

        >>> attempt(lambda: 1).map(str).unwrap()
        '1'
        >>> attempt(lambda: 1 / 0).map(str).unwrap()
        Traceback (most recent call last):
        ...
        ZeroDivisionError: division by zero
        """
        return attempt(lambda: fn(self.fn()))
