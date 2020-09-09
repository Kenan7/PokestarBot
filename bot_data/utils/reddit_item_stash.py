import collections.abc
from typing import Any, Iterator, Mapping, Optional, Tuple, Type, Union

import asyncpraw.models

from .bounded_list import BoundedDict, BoundedList


class RedditItemStash(collections.abc.Mapping, Mapping[str, Union[BoundedList, BoundedDict]]):
    __slots__ = ("__dict__", "name", "constructor", "bound")

    name: str
    constructor: Union[Type[BoundedList], Type[BoundedDict]]
    bound: int

    @property
    def count(self) -> int:
        count = 0
        for val in vars(self).values():
            count += len(val)
        return count

    def __init__(self, name: Optional[str] = None, itemtype: Union[Type[BoundedList], Type[BoundedDict]] = BoundedList, bound: int = 10):
        self.name = name or "Unnamed"
        self.constructor = itemtype
        self.bound = bound

    def __repr__(self) -> str:
        return f"<Stash name={repr(self.name)} constructor={self.constructor.__name__} subreddits={len(self)} total_items={self.count}>"

    def __getitem__(self, k: str) -> Union[BoundedList, BoundedDict]:
        return getattr(self, k)

    def __len__(self) -> int:
        return len(vars(self))

    def __iter__(self) -> Iterator[Tuple[str, Union[BoundedList, BoundedDict]]]:
        return iter(vars(self).items())

    def setdefault(self, subreddit_name: str) -> Union[BoundedDict, BoundedList]:
        if not hasattr(self, subreddit_name):
            setattr(self, subreddit_name, self.constructor(bound=self.bound))
        return getattr(self, subreddit_name)

    def add(self, item: Union[asyncpraw.models.Submission, asyncpraw.models.Comment, asyncpraw.models.ModAction], item_second: Optional[Any] = None):
        subreddit = str(item.subreddit) if hasattr(item, "subreddit") else "all"
        container = self.setdefault(subreddit)
        if isinstance(container, BoundedList):
            return container.append(item)
        else:
            container[item] = item_second

    def check(self, item: Union[asyncpraw.models.Submission, asyncpraw.models.Comment, asyncpraw.models.ModAction],
              item_second: Optional[Any] = None) -> bool:
        """Check if the object is in any of the instance's lists/dictionaries."""
        if hasattr(item, "subreddit"):
            subreddit_name = str(item.subreddit)
            if value := getattr(self, subreddit_name, None):
                if isinstance(value, BoundedDict):
                    if item not in value:
                        return False
                    else:
                        return value[item] == item_second
                else:
                    return item in value
            else:
                return False
        else:  # Fallback, search all subreddits
            for container in vars(self).values():
                if isinstance(container, BoundedDict):
                    if item not in container:
                        return False
                    else:
                        return container[item] == item_second
                else:
                    if item in container:
                        return True
            return False  # Not in any containers
