from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.base.Query import Query
from gdo.core.GDT_Container import GDT_Container
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard
from gdo.forum.GDT_Board import GDT_Board
from gdo.table.MethodQueryCards import MethodQueryCards
from gdo.ui.GDT_Link import GDT_Link
from gdo.ui.GDT_Menu import GDT_Menu


class boards(MethodQueryCards):
    """Render the direct children of one forum board as cards."""

    def gdo_needs_authentication(self) -> bool:
        return False

    def gdo_parameters(self) -> list[GDT]:
        return [GDT_Board('board').not_null().initial('1')]

    def gdo_has_permission(self, user) -> bool:
        return self.param_value('board').has_permission(user)

    def gdo_table(self) -> GDO:
        return GDO_ForumBoard.table()

    def gdo_execute(self) -> GDT:
        return GDT_Container().vertical().add_fields(
            self.board_actions(),
            super().gdo_execute(),
        )

    def board_actions(self) -> GDT_Menu:
        board_id = self.param_value('board').get_id()
        module = self.gdo_module()
        return GDT_Menu().horizontal().add_fields(
            GDT_Link('new_board').
            href(module.href('board', f'&board_parent={board_id}')).
            text_raw('New board').icon('add'),
            GDT_Link('edit_board').
            href(module.href('board', f'&id={board_id}')).
            text_raw('Edit this board').icon('edit'),
            GDT_Link('new_thread').
            href(module.href('new_thread', f'&thread_board={board_id}')).
            text_raw('New thread').icon('add'),
        )

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
