from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.base.util.href import href
from gdo.forum.GDO_ForumThread import GDO_ForumThread
from gdo.forum.GDT_Board import GDT_Board
from gdo.table.GDT_Table import GDT_Table, TableMode
from gdo.table.MethodQueryTable import MethodQueryTable
from gdo.ui.GDT_Bar import GDT_Bar
from gdo.ui.GDT_Link import GDT_Link
from gdo.ui.GDT_Menu import GDT_Menu


class board(MethodQueryTable):

    def gdo_table_mode(self) -> TableMode:
        return TableMode.LIST

    def gdo_table(self) -> GDO:
        return GDO_ForumThread.table()

    def gdo_parameters(self) -> list[GDT]:
        return [
            GDT_Board('id').not_null(),
        ]

    def gdo_execute(self) -> GDT:
        table = super().gdo_execute()
        menu = GDT_Menu().add_field(GDT_Link().href(href('forum', 'addthread', f'&bid={self.param_val('id')}')).text('btn_add_thread'))
        return GDT_Bar().vertical().add_fields(table, menu)
