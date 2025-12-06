from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.forum.GDO_ForumThread import GDO_ForumThread
from gdo.table.MethodQueryTable import MethodQueryTable


class latest(MethodQueryTable):

    def gdo_searched(self) -> bool:
        return False

    def gdo_table(self) -> GDO:
        return GDO_ForumThread.table()

    def gdo_table_headers(self) -> list[GDT]:
        t = self.gdo_table()
        return [
            t.column('thread_postcount'),
            t.column('thread_title'),
            t.column('thread_creator'),
        ]

