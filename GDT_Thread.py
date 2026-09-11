from gdo.core.GDT_ObjectSelect import GDT_ObjectSelect
from gdo.forum.GDO_ForumThread import GDO_ForumThread


class GDT_Thread(GDT_ObjectSelect):
    """Select one forum discussion thread by title or identifier."""

    def __init__(self, name: str):
        super().__init__(name)
        self.table(GDO_ForumThread.table())
