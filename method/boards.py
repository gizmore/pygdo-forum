from gdo.base.GDO import GDO
from gdo.base.Application import Application
from gdo.base.GDT import GDT
from gdo.base.Query import Query
from gdo.base.Render import Mode
from gdo.base.Render import Render
from gdo.base.Trans import t
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
from gdo.forum.LastPostTime import render_last_post_time


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
            return self.gdo_table().select_with_stats(super().gdo_table_query()).where('1=0').nocache()
        left, right = int(current['board_tree_left']), int(current['board_tree_right'])
        all_boards = list(self.gdo_table().select().nocache().exec())
        self._visible_tree = self.visible_tree(all_boards, GDO_User.current())
        self._subtree_stats_cache = {}
        visible = [int(child.get_id()) for child in self._visible_tree]
        return self.gdo_table().select_with_stats(super().gdo_table_query()).where(
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

    @staticmethod
    def visible_tree(all_boards, user):
        """Exclude denied boards and their descendants from aggregate statistics."""
        ordered = sorted(all_boards, key=lambda board: int(board.get_left()))
        ancestors = []
        visible = []
        for board in ordered:
            left, right = int(board.get_left()), int(board.get_right())
            while ancestors and left > ancestors[-1][0]:
                ancestors.pop()
            allowed = board.has_permission(user) and all(item[1] for item in ancestors)
            ancestors.append((right, allowed))
            if allowed:
                visible.append(board)
        return visible

    def subtree_stats(self, board):
        """Return visible descendant thread count, replies and last post."""
        if not hasattr(self, '_visible_tree'):
            self._visible_tree = self.visible_tree(list(self.gdo_table().select().nocache().exec()), GDO_User.current())
            self._subtree_stats_cache = {}
        board_id = str(board.get_id())
        if board_id not in self._subtree_stats_cache:
            current = next((item for item in self._visible_tree if str(item.get_id()) == board_id), None)
            if current is None:
                return (0, 0, None)
            left, right = int(current.get_left()), int(current.get_right())
            ids = [int(item.get_id()) for item in self._visible_tree
                   if left <= int(item.get_left()) and int(item.get_right()) <= right]
            from gdo.forum.GDO_ForumPost import GDO_ForumPost
            from gdo.forum.GDO_ForumThread import GDO_ForumThread
            threads = GDO_ForumThread.table().gdo_table_name()
            posts = GDO_ForumPost.table().gdo_table_name()
            row = Application.db().select(
                f'SELECT COUNT(DISTINCT thread.thread_id), COUNT(post.post_id), '
                f'COUNT(DISTINCT post.post_thread), MAX(post.post_created) '
                f'FROM {threads} AS thread LEFT JOIN {posts} AS post ON post.post_thread=thread.thread_id '
                f'WHERE thread.thread_board IN ({",".join(map(str, ids))}) AND thread.thread_deleted IS NULL',
                False,
            ).fetch_row()
            self._subtree_stats_cache[board_id] = (int(row[0] or 0), int(row[1] or 0) - int(row[2] or 0), row[3])
        return self._subtree_stats_cache[board_id]

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
        return replies.val(str(self.subtree_stats(board)[1])).render_html()

    def render_num_threads(self, count: GDT_UInt, board: GDO_ForumBoard) -> str:
        return count.val(str(self.subtree_stats(board)[0])).render_html()

    def render_last_post_date(self, date: GDT_Date, board: GDO_ForumBoard) -> str:
        last_post = self.subtree_stats(board)[2]
        return render_last_post_time(last_post) if last_post else Render.italic(t('none'), Mode.render_html)
