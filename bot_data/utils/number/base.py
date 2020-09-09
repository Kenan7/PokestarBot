import abc
from typing import List, TYPE_CHECKING, Type, TypeVar, Union, overload

if TYPE_CHECKING:
    from .static_number import StaticNumber
    from .sum import Sum

_T = TypeVar("_T")


class NumberBase(abc.ABC):
    value: int
    lists: List[Union["Sum", "StaticNumber"]]

    @staticmethod
    @overload
    def get_value(item: Union["StaticNumber", "Sum"]) -> int:
        pass

    @staticmethod
    @overload
    def get_value(item: _T) -> _T:
        pass

    @staticmethod
    def get_value(item):
        if isinstance(item, NumberBase):
            return item.value
        return item

    def delete(self):
        for item in self.lists:
            item.remove(self)

    def __hex__(self):
        return hex(self.value)

    def __oct__(self):
        return oct(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __float__(self) -> float:
        return float(self.value)

    def __int__(self) -> int:
        return self.value

    def __new__(cls: Type[_T], *args, **kwargs) -> _T:
        instance = super().__new__(cls)
        instance.lists = []
        return instance
