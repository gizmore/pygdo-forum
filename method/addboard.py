from gdo.base.GDT import GDT
from gdo.base.util.href import href
from gdo.core.GDO_File import GDO_File
from gdo.core.GDT_Permission import GDT_Permission
from gdo.form.GDT_Form import GDT_Form
from gdo.form.MethodForm import MethodForm
from gdo.forum.module_forum import module_forum
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard
from gdo.forum.GDT_Board import GDT_Board
from gdo.ui.GDT_Image import GDT_Image
from gdo.ui.GDT_Title import GDT_Title


class addboard(MethodForm):

    def gdo_parameters(self) -> list[GDT]:
        return [
            GDT_Board('id').not_null(),
        ]

    def get_parent_board(self) -> GDO_ForumBoard:
        return self.param_value('bid', False) or self.param_value('id')

    def get_board_image(self) -> GDO_File:
        return self.param_value('board_image') or module_forum.instance().cfg_default_board_image()

    def gdo_create_form(self, form: GDT_Form) -> None:
        form.add_fields(
            GDT_Board('bid').initial(self.param_val('id')).label('parent_board'),
            GDT_Title('title').not_null(),
            GDT_Permission('perm').label('permission'),
            GDT_Image('image'),
        )
        super().gdo_create_form(form)

    async def form_submitted(self):
        board = GDO_ForumBoard.blank({
            'board_parent': self.get_parent_board().get_id(),
            'board_title': self.param_value('title'),
            'board_permission': self.param_val('perm'),
            'board_image': self.get_board_image().get_id(),
        }).insert()
        self.msg('msg_forum_board_added', (board.get_id(),))
        return self.redirect(href('forum', 'boards', f'&id={board.get_id()}'))
