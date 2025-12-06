from gdo.core.GDT_ObjectSelect import GDT_ObjectSelect
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard


class GDT_Board(GDT_ObjectSelect):

    def __init__(self, name: str):
        super().__init__(name)
        self.table(GDO_ForumBoard.table())
