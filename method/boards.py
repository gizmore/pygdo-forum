from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.base.Method import Method
from gdo.base.util.href import href
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard
from gdo.forum.GDO_ForumThread import GDO_ForumThread
from gdo.forum.GDT_Board import GDT_Board
from gdo.forum.method.latest import latest
from gdo.table.GDT_Table import TableMode
from gdo.table.MethodQueryTable import MethodQueryTable
from gdo.ui.GDT_Bar import GDT_Bar
from gdo.ui.GDT_Link import GDT_Link
from gdo.ui.GDT_Menu import GDT_Menu
from gdo.ui.GDT_TreeView import GDT_TreeView


class boards(MethodQueryTable):

    def gdo_table_mode(self) -> TableMode:
        return TableMode.LIST

    def gdo_searched(self) -> bool:
        return False

    def gdo_parameters(self) -> list[GDT]:
        return [
            GDT_Board('id').not_null().initial('1'),
        ]

    def gdo_table(self) -> GDO:
        return GDO_ForumThread.table()

    def gdo_execute(self) -> GDT:
        table = super().gdo_execute()
        menu = GDT_Menu().add_field(GDT_Link().href(href('forum', 'addboard', f'&id={self.param_val('id')}')).text('btn_add_board'))
        gdt = GDT_Bar().vertical()
        if self.param_val('id') == '1':
            gdt.add_field(latest())
        tree = GDT_TreeView('boards').query(GDO_ForumBoard.table().select().order('board_parent, board_sort')).parent_col('board_parent')
        return gdt.add_fields(tree, table, menu)
