from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.base.Application import Application
from gdo.form.GDT_CSRF import GDT_CSRF
from gdo.form.GDT_Form import GDT_Form
from gdo.form.MethodCrud import MethodCrud
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard
from gdo.forum.GDT_ForumBoard import GDT_ForumBoard
from gdo.forum.GDO_ForumThread import GDO_ForumThread
from gdo.forum.ForumAccess import ForumPostForm, ForumStaffAccess


class board_crud(ForumStaffAccess, ForumPostForm, MethodCrud):
    """Staff editor for forum board metadata and tree placement."""

    def gdo_method_hidden(self) -> bool:
        return True

    def gdo_table(self) -> GDO:
        return GDO_ForumBoard.table()

    def gdo_user_permission(self) -> str:
        return 'staff'

    def gdo_form_fields(self, gdo: GDO) -> list[GDT]:
        return [gdo.column('board_name'), gdo.column('board_title'), gdo.column('board_threads_allowed'), gdo.column('board_icon'), gdo.column('board_permission')]

    def form_values(self) -> dict[str, str]:
        return {name: self.param_val(name) for name in (
            'board_name', 'board_title', 'board_threads_allowed', 'board_icon', 'board_permission')}

    def gdo_create_form(self, form: GDT_Form) -> None:
        board = self.crud_gdo()
        if Application.IS_HTTP:
            form.add_field(GDT_CSRF())
        form.add_field((board or self.gdo_table()).column('board_name'))
        form.add_field((board or self.gdo_table()).column('board_title'))
        form.add_field((board or self.gdo_table()).column('board_threads_allowed'))
        form.add_field((board or self.gdo_table()).column('board_icon'))
        form.add_field((board or self.gdo_table()).column('board_permission'))
        if board:
            parent = board.parent()
            form.add_field(
                GDT_ForumBoard('board_parent').label('parent').for_child(board).
                initial(parent.get_id() if parent else None).
                writable(parent is not None)
            )
            form.actions().add_field(self.crud_edit_button())
            form.actions().add_field(self.crud_delete_button())
        else:
            form.add_field(GDT_ForumBoard('board_parent').label('parent').not_null())
            form.actions().add_field(self.crud_create_button())

    def on_create(self):
        parent = self.param_value('board_parent')
        created = GDO_ForumBoard.create_child(
            parent,
            self.param_val('board_title'),
            self.param_val('board_icon'),
            self.param_val('board_permission'),
            self.param_val('board_name'),
            self.param_val('board_threads_allowed'),
        )
        self.msg('msg_forum_board_created', (created.render_name(),))
        return self.get_form()

    def on_update(self):
        board = self.crud_gdo()
        parent = self.param_value('board_parent', False)
        if self.get_form().get_field('board_parent').is_writable() and not parent:
            self.err('err_forum_board_invalid_parent')
            return self.get_form()
        if parent:
            board.move_to(parent)
        return super().on_update()

    def on_delete(self):
        board = self.crud_gdo()
        rows = GDO_ForumBoard.lock_tree()
        bounds = rows.get(board.get_id())
        if not bounds:
            self.err('err_forum_board_not_empty')
            return self.get_form()
        left, right = bounds
        has_parent = any(a < left and b > right for a, b in rows.values())
        has_children = any(a > left and b < right for a, b in rows.values())
        threads = GDO_ForumThread.table().gdo_table_name()
        has_threads = Application.db().select(
            f'SELECT thread_id FROM {threads} WHERE thread_board={int(board.get_id())} LIMIT 1 FOR UPDATE',
            False).fetch_row()
        if not has_parent or has_children or has_threads:
            self.err('err_forum_board_not_empty')
            return self.get_form()
        return super().on_delete()
