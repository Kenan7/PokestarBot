import collections
from typing import AsyncIterable, AsyncIterator, Tuple, TypeVar

_T = TypeVar("_T")


class aenumerate(collections.abc.AsyncIterator, AsyncIterator[Tuple[int, _T]]):
    """enumerate for async for"""

    def __init__(self, aiterable: AsyncIterable[_T], start: int = 0):
        self._aiterable = aiterable
        self._i = start - 1

    async def __aiter__(self):
        self._ait = await self._aiterable.__aiter__()
        return self

    async def __anext__(self) -> Tuple[int, _T]:
        # self._ait will raise the appropriate AsyncStopIteration
        val = await self._ait.__anext__()
        self._i += 1
        return self._i, val
