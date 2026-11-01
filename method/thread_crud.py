from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.base.Application import Application
from gdo.form.GDT_CSRF import GDT_CSRF
from gdo.form.MethodCrud import MethodCrud
from gdo.forum.GDO_ForumThread import GDO_ForumThread
from gdo.forum.GDT_Board import GDT_Board
from gdo.forum.ForumAccess import ForumPostForm, ForumStaffAccess


class thread_crud(ForumStaffAccess, ForumPostForm, MethodCrud):
    """Create and edit a thread's board and title.

    The creator and timestamp are structural metadata, filled by the thread
    model when it is inserted rather than supplied by the form.
    """

    def gdo_method_hidden(self) -> bool:
        return True

    def gdo_user_permission(self) -> str:
        return 'staff'

    def gdo_table(self) -> GDO:
        return GDO_ForumThread.table()

    def gdo_create_form(self, form):
        super().gdo_create_form(form)
        if self.crud_gdo():
            form.text('info_forum_thread_delete')
        if Application.IS_HTTP:
            form.add_field(GDT_CSRF())

    def gdo_parameters(self) -> list[GDT]:
        """Accept the board supplied by the ``New thread`` link.

        It is deliberately also a method parameter, rather than only a form
        field.  That makes the selected board available while the create form
        is built, so its value survives the initial GET request.
        """
        return [*super().gdo_parameters(), GDT_Board('thread_board')]

    def gdo_form_fields(self, gdo: GDO) -> list[GDT]:
        return [
            GDT_Board('thread_board').not_null().initial(
                self.param_val('thread_board', False) or gdo.gdo_val('thread_board')
            ),
            gdo.column('thread_title'),
        ]

    def form_values(self) -> dict[str, str]:
        return {name: self.param_val(name) for name in ('thread_board', 'thread_title')}

    def on_delete(self):
        return super().on_delete()
