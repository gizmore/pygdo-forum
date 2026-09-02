from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.core.GDT_AutoInc import GDT_AutoInc
from gdo.core.GDT_Tree import GDT_Tree
from gdo.ui.GDT_Title import GDT_Title


class GDO_ForumBoard(GDO):

    def gdo_columns(self) -> list[GDT]:
        return [
            GDT_AutoInc('board_id'),
            GDT_Title('board_title').not_null(),
            GDT_Tree('board_tree').not_null(),
        ]

    def render_name(self):
        return self.gdo_val('board_title')
