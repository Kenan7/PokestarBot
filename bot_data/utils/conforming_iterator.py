import sqlite3


class ConformingIterator(tuple):
    def __conform__(self, protocol):
        if protocol is sqlite3.PrepareProtocol:
            return str(self)

    def __repr__(self):
        return f"{type(self).__name__}{super().__repr__()}"

    def __str__(self):
        return super().__repr__()
