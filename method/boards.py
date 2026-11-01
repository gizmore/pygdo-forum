from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.base.Query import Query
from gdo.base.Render import Mode
from gdo.core.GDT_Int import GDT_Int
from gdo.core.GDT_Container import GDT_Container
from gdo.core.GDT_UInt import GDT_UInt
from gdo.core.GDO_User import GDO_User
from gdo.date.GDT_Created import GDT_Created
from gdo.date.GDT_Date import GDT_Date
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard
from gdo.forum.GDT_Board import GDT_Board
from gdo.table.MethodQueryTable import MethodQueryTable
from gdo.ui.GDT_Link import GDT_Link
from gdo.ui.GDT_Button import GDT_Button
from gdo.ui.GDT_Menu import GDT_Menu
from gdo.forum.ForumAccess import ForumAccess


class boards(ForumAccess, MethodQueryTable):
    """Render the direct children of one forum board as cards."""

    def gdo_method_hidden(self) -> bool:
        return True

    def gdo_needs_authentication(self) -> bool:
        return False

    def gdo_paginated(self) -> bool:
        return False

    def gdo_ordered(self) -> bool:
        return False

    def gdo_filtered(self) -> bool:
        return False

    def gdo_searched(self) -> bool:
        return False

    def gdo_parameters(self) -> list[GDT]:
        return [GDT_Board('board').not_null().initial('1')]

    def gdo_has_permission(self, user) -> bool:
        board = self.param_value('board', False)
        return bool(board and board.has_permission(user))

    def gdo_table(self) -> GDO:
        return GDO_ForumBoard.table()

    def gdo_table_query(self) -> Query:
        board = self.get_board()
        table = self.gdo_table().gdo_table_name()
        current = self.gdo_table().select('board_tree_left, board_tree_right').where(
            f'board_id={int(board.get_id())}'
        ).nocache().exec().fetch_assoc()
        if not current:
            return super().gdo_table_query().where('1=0').nocache()
        left, right = int(current['board_tree_left']), int(current['board_tree_right'])
        visible = [int(child.get_id()) for child in self.gdo_table().select().nocache().exec()
                   if child.has_permission(GDO_User.current())]
        return super().gdo_table_query().where(
            f'board_tree_left>{left} AND board_tree_right<{right} '
            f'AND NOT EXISTS (SELECT 1 FROM {table} AS ancestor '
            f'WHERE ancestor.board_tree_left>{left} '
            f'AND ancestor.board_tree_right<{right} '
            f'AND ancestor.board_tree_left<{table}.board_tree_left '
            f'AND ancestor.board_tree_right>{table}.board_tree_right)'
        ).where(f"board_id IN ({','.join(map(str, visible)) or 'NULL'})").nocache()

    def gdo_execute(self) -> GDT:
        result = GDT_Container().vertical().add_field(self.board_actions())
        if self.get_num_results():
            result.add_field(super().gdo_execute())
        return result

    def get_board(self) -> GDO_ForumBoard:
        return self.param_value('board')

    def board_actions(self) -> GDT_Menu:
        board = self.get_board()
        board_id = board.get_id()
        module = self.gdo_module()
        user = GDO_User.current()
        menu = GDT_Menu().horizontal()
        if user.is_staff():
            menu.add_fields(
                GDT_Link('new_board').href(module.href('board_crud', f'&board_parent={board_id}')).text('btn_new_board').icon('add'),
                GDT_Link('edit_board').href(module.href('board_crud', f'&id={board_id}')).text('btn_edit_board').icon('edit'),
            )
        if user.is_authenticated() and board.is_thread_allowed():
            menu.add_field(GDT_Link('new_thread').href(module.href('new_thread', f'&thread_board={board_id}')).text('btn_add_thread').icon('add'))
        return menu

    def gdo_table_headers(self) -> list[GDT]:
        module = self.gdo_module()
        return [
            GDT_Button('board_title').label('title').href(module.href('forum', '&id=%ID%')),
            GDT_Int('replies').label('replies').shrink(),
            GDT_Date('last_post_date'),
            GDT_UInt('num_threads').shrink(),
        ]

    def render_board_title(self, button: GDT_Button, board: GDO_ForumBoard) -> str:
        return button.text_raw(board.render_name()).render_html()

    def render_gdo(self, board: GDO_ForumBoard, mode: Mode):
        if mode in (Mode.render_txt, Mode.render_cli, Mode.render_irc):
            return f'{board.get_id()}-{board.render_name()}'
        return super().render_gdo(board, mode)

    def render_replies(self, replies: GDT_Int, board: GDO_ForumBoard) -> str:
        return replies.val(str(board.num_replies())).render_html()

    # def render_last_post_date(self, date: GDT_Created, board: GDO_ForumBoard) -> str:
    #     if last_post := board.last_post_date():
    #         return date.val(last_post).render_html()
    #     return ''
