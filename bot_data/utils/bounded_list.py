import logging
from typing import Any, Iterable, Mapping, Tuple, TypeVar, overload

logger = logging.getLogger(__name__)

_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


class BoundedList(list):
    def __init__(self, bound: int = 100):
        super().__init__()
        self.bound = bound

    def evict(self):
        if len(self) > self.bound:
            for item in self[:-self.bound]:
                self.remove(item)

    def append(self, obj):
        super().append(obj)
        self.evict()

    def extend(self, iterable: Iterable[Any]):
        super().extend(iterable)
        self.evict()

    def insert(self, index: int, obj):
        super().insert(index, obj)
        self.evict()

    def __add__(self, x):
        data = super().__add__(x)
        self.evict()
        return data

    def __repr__(self) -> str:
        return "<{} bound={} values={}>".format(type(self).__name__, self.bound, super().__repr__())

    def __iadd__(self, x: Iterable[Any]):
        data = super().__iadd__(x)
        self.evict()
        return data

    __slots__ = ("bound",)


class BoundedDict(dict):

    def __init__(self, bound: int = 100):
        super().__init__()
        self.bound = bound

    def setdefault(self, key: _KT, default: _VT = ...) -> _VT:
        if len(self) == self.bound and key not in self:
            del self[next(iter(self.keys()))]
        return super().setdefault(key, default)

    @overload
    def update(self, m: Mapping[_KT, _VT], **kwargs: _VT):
        ...

    @overload
    def update(self, m: Iterable[Tuple[_KT, _VT]], **kwargs: _VT):
        ...

    @overload
    def update(self, **kwargs: _VT):
        ...

    def update(self, m: Mapping[_KT, _VT], **kwargs: _VT):
        for key, value in {**m, **kwargs}.items():
            self.__setitem__(key, value)

    def __repr__(self) -> str:
        return "<{} bound={} values={}>".format(type(self).__name__, self.bound, super().__repr__())

    def __setitem__(self, k: _KT, v: _VT):
        if len(self) == self.bound and k not in self:
            del self[next(iter(self.keys()))]
        super().__setitem__(k, v)

    __slots__ = ("bound",)
