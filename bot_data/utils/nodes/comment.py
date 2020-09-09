from typing import Iterable, Optional, Union

import anytree
import asyncpraw.models


class CommentNode(anytree.NodeMixin):
    __slots__ = ("comment", "parent", "_children", "full")

    CHILDREN_ATTR = "replies"

    def __init__(self, comment: asyncpraw.models.Comment, parent: Optional["CommentNode"] = None, full: bool = False):
        self.comment = comment
        self.parent = parent
        self.full = full
        self._children = None

    @property
    def children(self):
        return self._children or [CommentNode(comment, self) for comment in getattr(self.comment, self.CHILDREN_ATTR) if
                                  isinstance(comment, asyncpraw.models.Comment)]

    @children.setter
    def children(self, new_children: Iterable[Union[asyncpraw.models.Comment, "CommentNode"]]):
        self._children = [CommentNode(comment, self) if not isinstance(comment, CommentNode) else comment for comment in new_children]
        for child in self._children:
            child.parent = self

    @property
    def lines(self):
        return repr(self).splitlines(False)

    def __repr__(self):
        text = self.comment.body.replace("\n\n", "\0").replace("\n", " ").replace("\0", "\n")
        if len(text) > 300 and not self.full:
            text = text[:297] + "..."
        author_name = getattr(self.comment.author, "name", "").replace('_', '\\_') or '[deleted]'
        return f"u/{author_name}: {text.rstrip() or '[deleted]'}"


class SubmissionNode(CommentNode):
    CHILDREN_ATTR = "comments"

    def __init__(self, submission: asyncpraw.models.Submission):
        super().__init__(submission)

    def __repr__(self):
        author_name = getattr(self.comment.author, "name", "").replace('_', '\\_') or '[deleted]'
        return f"u/{author_name}: {self.comment.title.rstrip()}"
