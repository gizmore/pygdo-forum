from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.form.MethodCrud import MethodCrud
from gdo.forum.GDO_ForumThread import GDO_ForumThread
from gdo.forum.GDT_Board import GDT_Board


class thread_crud(MethodCrud):
    """Create and edit a thread's board and title.

    The creator and timestamp are structural metadata, filled by the thread
    model when it is inserted rather than supplied by the form.
    """

    def gdo_table(self) -> GDO:
        return GDO_ForumThread.table()

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
