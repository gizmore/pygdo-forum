from gdo.base.GDO import GDO
from gdo.base.Query import Query
from gdo.base.Render import Mode
from gdo.forum.GDO_ForumThread import GDO_ForumThread
from gdo.forum.GDT_Board import GDT_Board
from gdo.table.GDT_Table import TableMode
from gdo.table.MethodQueryTable import MethodQueryTable


class chatboard(MethodQueryTable):
    """List one board's threads in a text connector."""

    @classmethod
    def gdo_trigger(cls) -> str:
        return 'forum.board'

    def gdo_parameters(self):
        return [GDT_Board('id').not_null()]

    def gdo_table(self) -> GDO:
        return GDO_ForumThread.table()

    def gdo_table_mode(self) -> TableMode:
        return TableMode.LIST

    def gdo_searched(self) -> bool:
        return False

    def gdo_filtered(self) -> bool:
        return False

    def gdo_ordered(self) -> bool:
        return False

    def gdo_table_query(self) -> Query:
        board = self.param_value('id')
        return self.gdo_table().select().where(
            f'thread_board={self.gdo_table().quote(board.get_id())}'
        ).order('thread_id DESC')

    def render_gdo(self, thread: GDO_ForumThread, mode: Mode) -> str:
        return f'{thread.get_id()}: {thread.gdo_val("thread_title")}'
