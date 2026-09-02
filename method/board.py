from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.core.GDT_Object import GDT_Object
from gdo.form.GDT_Form import GDT_Form
from gdo.form.GDT_Submit import GDT_Submit
from gdo.form.MethodCrud import MethodCrud
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard


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
            form.actions().add_field(
                GDT_Submit('update').calling(self.on_update).default_button()
            )
        else:
            form.add_field(
                GDT_Object('board_parent').table(self.gdo_table()).not_null()
            )
            form.actions().add_field(
                GDT_Submit('create').calling(self.on_create).default_button()
            )

    def on_create(self):
        parent = self.param_value('board_parent')
        created = GDO_ForumBoard.create_child(parent, self.param_val('board_title'))
        self.msg('msg_crud_created', (created.render_name(),))
        return self.get_form()
