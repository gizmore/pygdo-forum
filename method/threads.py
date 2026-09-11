from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.base.Query import Query
from gdo.forum.GDO_ForumThread import GDO_ForumThread
from gdo.forum.GDT_Board import GDT_Board
from gdo.table.MethodQueryList import MethodQueryList


class threads(MethodQueryList):
    """List the discussion threads belonging directly to one forum board."""

    def gdo_needs_authentication(self) -> bool:
        return False

    def gdo_parameters(self) -> list[GDT]:
        return [GDT_Board('board').not_null().initial('1')]

    def gdo_has_permission(self, user) -> bool:
        return self.param_value('board').has_permission(user)

    def gdo_table(self) -> GDO:
        return GDO_ForumThread.table()

    def gdo_table_headers(self) -> list[GDT]:
        table = self.gdo_table()
        return [
            table.column('thread_title'),
            table.column('thread_creator'),
            table.column('thread_created'),
        ]

    def gdo_table_query(self) -> Query:
        board = self.param_value('board')
        return self.gdo_table().select().where(
            f'thread_board={board.get_id()}'
        ).order('thread_created DESC')
