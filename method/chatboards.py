from gdo.base.GDO import GDO
from gdo.base.Query import Query
from gdo.base.Render import Mode
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard
from gdo.table.GDT_Table import TableMode
from gdo.table.MethodQueryTable import MethodQueryTable


class chatboards(MethodQueryTable):
    """A compact, connector-safe board list for IRC and Telegram."""

    @classmethod
    def gdo_trigger(cls) -> str:
        return 'forum.boards'

    def gdo_table(self) -> GDO:
        return GDO_ForumBoard.table()

    def gdo_table_mode(self) -> TableMode:
        return TableMode.LIST

    def gdo_searched(self) -> bool:
        return False

    def gdo_filtered(self) -> bool:
        return False

    def gdo_ordered(self) -> bool:
        return False

    def gdo_table_query(self) -> Query:
        return self.gdo_table().select().where(
            'board_hidden=0 OR board_hidden IS NULL'
        ).order('board_sort, board_id')

    def render_gdo(self, board: GDO_ForumBoard, mode: Mode) -> str:
        return f'{board.get_id()}: {board.gdo_val("board_title")}'
