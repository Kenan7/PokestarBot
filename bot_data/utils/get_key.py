from typing import Dict, TypeVar, Optional

_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


def get_key(my_dict: Dict[_KT, _VT], val: _VT) -> Optional[_KT]:
    for key, value in my_dict.items():
        if val == value:
            return key
