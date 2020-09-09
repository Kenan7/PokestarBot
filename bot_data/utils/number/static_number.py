import numbers
from typing import Any, Iterable, Optional, SupportsBytes, Tuple, Union

from .base import NumberBase

NotImplementedType = type(NotImplemented)


class StaticNumber(NumberBase, numbers.Integral):

    def __long__(self) -> int:
        return int(self)

    def __div__(self, other) -> NotImplementedType:
        return NotImplemented

    def __rdiv__(self, other) -> NotImplementedType:
        return NotImplemented

    def __init__(self, value: int = 0):
        self.value = value

    __slots__ = ("lists",)

    def as_integer_ratio(self) -> Tuple[int, int]:
        return self.value, 1

    @property
    def real(self) -> int:
        return self.value

    @property
    def imag(self) -> int:
        return 0

    @property
    def numerator(self) -> int:
        return self.value

    @property
    def denominator(self) -> int:
        return 1

    def conjugate(self) -> int:
        return self.value

    def bit_length(self) -> int:
        return int.bit_length(self.value)

    def to_bytes(self, length: int, byteorder: str, *, signed: bool = ...) -> bytes:
        return int.to_bytes(self.value, length, byteorder, signed=signed)

    @classmethod
    def from_bytes(cls, byte: Union[Iterable[int], SupportsBytes], byteorder: str, *, signed: bool = ...) -> int:
        return int.from_bytes(byte, byteorder, signed=signed)

    def __add__(self, x: int) -> "StaticNumber":
        val = self.value + self.get_value(x)
        self.value = val
        return self

    def __sub__(self, x: int) -> "StaticNumber":
        val = self.value - self.get_value(x)
        self.value = val
        return self

    def __mul__(self, x: int) -> "StaticNumber":
        val = self.value * self.get_value(x)
        self.value = val
        return self

    def __floordiv__(self, x: int) -> "StaticNumber":
        val = self.value // self.get_value(x)
        self.value = val
        return self

    def __truediv__(self, x: int) -> float:
        return self.value / self.get_value(x)

    def __mod__(self, x: int) -> "StaticNumber":
        val = self.value % self.get_value(x)
        self.value = val
        return self

    def __divmod__(self, x: int) -> Tuple[int, int]:
        return divmod(self.value, self.get_value(x))

    def __radd__(self, x: int) -> "StaticNumber":
        val = self.get_value(x) + self.value
        self.value = val
        return self

    def __rsub__(self, x: int) -> "StaticNumber":
        val = self.get_value(x) - self.value
        self.value = val
        return self

    def __rmul__(self, x: int) -> "StaticNumber":
        val = self.get_value(x) - self.value
        self.value = val
        return self

    def __rfloordiv__(self, x: int) -> "StaticNumber":
        val = self.get_value(x) // self.value
        self.value = val
        return self

    def __rtruediv__(self, x: int) -> float:
        return self.get_value(x) / self.value

    def __rmod__(self, x: int) -> "StaticNumber":
        val = self.get_value(x) % self.value
        self.value = val
        return self

    def __rdivmod__(self, x: int) -> Tuple[int, int]:
        return divmod(self.get_value(x), self.value)

    def __pow__(self, /, x: int, mod: Optional[int] = ...) -> Any:
        return pow(self.value, self.get_value(x), mod)

    def __rpow__(self, /, x: int, mod: Optional[int] = ...) -> Any:
        return pow(self.get_value(x), self.value, mod)

    def __and__(self, n: int) -> "StaticNumber":
        val = self.value & self.get_value(n)
        self.value = val
        return self

    def __or__(self, n: int) -> "StaticNumber":
        val = self.value | self.get_value(n)
        self.value = val
        return self

    def __xor__(self, n: int) -> "StaticNumber":
        val = self.value ^ self.get_value(n)
        self.value = val
        return self

    def __lshift__(self, n: int) -> "StaticNumber":
        val = self.value << self.get_value(n)
        self.value = val
        return self

    def __rshift__(self, n: int) -> "StaticNumber":
        val = self.value >> self.get_value(n)
        self.value = val
        return self

    def __rand__(self, n: int) -> "StaticNumber":
        val = self.get_value(n) & self.value
        self.value = val
        return self

    def __ror__(self, n: int) -> "StaticNumber":
        val = self.get_value(n) | self.value
        self.value = val
        return self

    def __rxor__(self, n: int) -> "StaticNumber":
        val = self.get_value(n) ^ self.value
        self.value = val
        return self

    def __rlshift__(self, n: int) -> "StaticNumber":
        val = self.get_value(n) << self.value
        self.value = val
        return self

    def __rrshift__(self, n: int) -> "StaticNumber":
        val = self.get_value(n) >> self.value
        self.value = val
        return self

    def __neg__(self) -> "StaticNumber":
        val = -self.value
        self.value = val
        return self

    def __pos__(self) -> "StaticNumber":
        val = +self.value
        self.value = val
        return self

    def __invert__(self) -> "StaticNumber":
        val = ~self.value
        self.value = val
        return self

    def __trunc__(self) -> "StaticNumber":
        return self

    def __ceil__(self) -> "StaticNumber":
        return self

    def __floor__(self) -> "StaticNumber":
        return self

    def __round__(self, ndigits: Optional[int] = ...) -> "StaticNumber":
        return self

    def __getnewargs__(self) -> Tuple[int]:
        return int.__getnewargs__(self.value)

    def __eq__(self, x: object) -> bool:
        return self.value == self.get_value(x)

    def __ne__(self, x: object) -> bool:
        return self.value != self.get_value(x)

    def __lt__(self, x: int) -> bool:
        return self.value < self.get_value(x)

    def __le__(self, x: int) -> bool:
        return self.value <= self.get_value(x)

    def __gt__(self, x: int) -> bool:
        return self.value > self.get_value(x)

    def __ge__(self, x: int) -> bool:
        return self.value >= self.get_value(x)

    def __hash__(self) -> "StaticNumber":
        val = hash(self.value)
        self.value = val
        return self

    def __bool__(self) -> bool:
        return bool(self.value)

    def __index__(self) -> "StaticNumber":
        return self

    def __abs__(self) -> "StaticNumber":
        val = abs(self.value)
        self.value = val
        return self

    def __repr__(self):
        return f"StaticNumber({self.value})"
