from typing import Any, Callable, Iterable, Optional, Union

from .base import NumberBase
from .static_number import StaticNumber


class Sum(NumberBase, list):
    def __init__(self, *values: Union[StaticNumber, "Sum"]):
        super().__init__()
        self.extend(values)

    @property
    def value(self):
        return sum(map(lambda item: item.value, self))

    def sort(self, *, key: Optional[Callable[[Any], Any]] = lambda item: item.value, reverse: bool = ...) -> None:
        super().sort(key=key, reverse=reverse)

    def __repr__(self):
        return f"Sum<sum={self.value}, values={super().__repr__()}>"

    def make_sub_sum(self, *values: Union[StaticNumber, "Sum"]):
        sum_obj = type(self)(*values)
        self.append(sum_obj)
        return sum_obj

    def make_static_number(self, value: int = 0):
        num_obj = StaticNumber(value)
        self.append(num_obj)
        return num_obj

    def blank(self):
        for item in self:
            if isinstance(item, StaticNumber):
                item.value = 0
            elif isinstance(item, type(self)):
                item.blank()

    def append(self, obj: Any):
        if isinstance(obj, StaticNumber):
            obj.lists.append(self)
        super().append(obj)

    def extend(self, iterable: Iterable[Any]):
        copy = list(iterable)
        for item in copy:
            if isinstance(item, StaticNumber):
                item.lists.append(self)
        super().extend(iterable)

    def insert(self, index: int, obj: Any):
        if isinstance(obj, StaticNumber):
            obj.lists.append(self)
        super().insert(index, obj)

    __slots__ = ("lists",)
