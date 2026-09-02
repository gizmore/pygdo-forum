from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.base.Query import Query
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard
from gdo.forum.GDT_Board import GDT_Board
from gdo.table.MethodQueryCards import MethodQueryCards


class boards(MethodQueryCards):
    """Render the direct children of one forum board as cards."""

    def gdo_needs_authentication(self) -> bool:
        return False

    def gdo_parameters(self) -> list[GDT]:
        return [GDT_Board('board').not_null().initial('1')]

    def gdo_table(self) -> GDO:
        return GDO_ForumBoard.table()

    def gdo_table_headers(self) -> list[GDT]:
        return [self.gdo_table().column('board_title')]

    def gdo_table_query(self) -> Query:
        parent = self.param_value('board')
        left, right = parent.column('board_tree').get_value()
        table = self.gdo_table()
        table_name = table.gdo_table_name()
        return Query().table(f'{table_name} AS board').gdo(table).select().where(
            f'board_tree_left>{left} AND board_tree_right<{right} AND NOT EXISTS ('
            f'SELECT 1 FROM {table_name} AS ancestor '
            f'WHERE ancestor.board_tree_left>{left} AND ancestor.board_tree_right<{right} '
            f'AND ancestor.board_tree_left<board.board_tree_left '
            f'AND ancestor.board_tree_right>board.board_tree_right'
            f')'
        ).order('board_tree_left')

    def gdo_paginated(self) -> bool:
        return False

    def gdo_ordered(self) -> bool:
        return False

    def gdo_filtered(self) -> bool:
        return False

    def gdo_searched(self) -> bool:
        return False
