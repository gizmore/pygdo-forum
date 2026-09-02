from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.form.GDT_Form import GDT_Form
from gdo.form.GDT_Submit import GDT_Submit
from gdo.form.MethodCrud import MethodCrud
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard
from gdo.forum.GDT_ForumBoard import GDT_ForumBoard


class board(MethodCrud):
    """Staff editor for the metadata of an existing forum board."""

    def gdo_table(self) -> GDO:
        return GDO_ForumBoard.table()

    def gdo_user_permission(self) -> str:
        return 'staff'

    def gdo_form_fields(self, gdo: GDO) -> list[GDT]:
        return [gdo.column('board_title')]

    def gdo_create_form(self, form: GDT_Form) -> None:
        board = self.crud_gdo()
        form.add_field((board or self.gdo_table()).column('board_title'))
        if board:
            parent = board.parent()
            form.add_field(
                GDT_ForumBoard('board_parent').for_child(board).
                initial(parent.get_id() if parent else None).
                writable(parent is not None)
            )
            form.actions().add_field(
                GDT_Submit('update').calling(self.on_update).default_button()
            )
        else:
            form.add_field(
                GDT_ForumBoard('board_parent').not_null()
            )
            form.actions().add_field(
                GDT_Submit('create').calling(self.on_create).default_button()
            )

    def on_create(self):
        parent = self.param_value('board_parent')
        created = GDO_ForumBoard.create_child(parent, self.param_val('board_title'))
        self.msg('msg_crud_created', (created.render_name(),))
        return self.get_form()

    def on_update(self):
        board = self.crud_gdo()
        parent = self.param_value('board_parent', False)
        if parent and (current_parent := board.parent()) and parent.get_id() != current_parent.get_id():
            board.move_to(parent)
        return super().on_update()
