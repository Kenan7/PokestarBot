def rgb_string_from_int(value: int) -> str:
    base = hex(value)[2:]
    return "#" + base.zfill(6).lower()
