from gdo.core.GDT_Object import GDT_Object
from gdo.forum.GDO_ForumThread import GDO_ForumThread


class GDT_Thread(GDT_Object):

    def __init__(self, name: str):
        super().__init__(name)
        self.table(GDO_ForumThread.table())
        