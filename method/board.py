from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.form.MethodCrud import MethodCrud
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard


class board(MethodCrud):
    """Staff editor for the metadata of an existing forum board."""

    def gdo_table(self) -> GDO:
        return GDO_ForumBoard.table()

    def gdo_user_permission(self) -> str:
        return 'staff'

    def feature_create(self) -> bool:
        # Board insertion is a nested-set operation, not a generic CRUD one.
        return False

    def gdo_form_fields(self, gdo: GDO) -> list[GDT]:
        return [gdo.column('board_title')]
