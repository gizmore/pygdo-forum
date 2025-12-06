from gdo.base.GDO import GDO
from gdo.forum.GDO_ForumThread import GDO_ForumThread
from gdo.table.MethodQueryTable import MethodQueryTable


class latest(MethodQueryTable):

    def gdo_table(self) -> GDO:
        return GDO_ForumThread.table()

