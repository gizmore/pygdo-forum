from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.base.Application import Application
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

    @classmethod
    def create_child(cls, parent: 'GDO_ForumBoard', title: str) -> 'GDO_ForumBoard':
        """Append a board as the last child of ``parent``.

        The method owns the nested-set update, so callers never write tree
        boundaries directly.
        """
        tree = parent.column('board_tree')
        position = tree.get_right()
        table = cls.table()
        table_name = table.gdo_table_name()

        Application.db().query(
            f'UPDATE {table_name} SET board_tree_right=board_tree_right+2 '
            f'WHERE board_tree_right>={position}'
        )
        Application.db().query(
            f'UPDATE {table_name} SET board_tree_left=board_tree_left+2 '
            f'WHERE board_tree_left>{position}'
        )
        # Keep the caller's selected parent coherent for this request.
        tree.set_right(position + 2)
        return cls.blank({
            'board_title': title,
            'board_tree_left': str(position),
            'board_tree_right': str(position + 1),
        }).insert()
