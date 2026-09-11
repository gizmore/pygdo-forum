from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.core.GDT_AutoInc import GDT_AutoInc
from gdo.core.GDT_Creator import GDT_Creator
from gdo.core.GDT_Object import GDT_Object
from gdo.date.GDT_Created import GDT_Created
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard
from gdo.ui.GDT_Title import GDT_Title


class GDO_ForumThread(GDO):
    """A discussion thread, located directly in one forum board."""

    def gdo_columns(self) -> list[GDT]:
        return [
            GDT_AutoInc('thread_id'),
            GDT_Object('thread_board').table(GDO_ForumBoard.table()).not_null().cascade_delete(),
            GDT_Title('thread_title').not_null(),
            GDT_Creator('thread_creator'),
            GDT_Created('thread_created'),
        ]

    def render_name(self):
        return self.gdo_val('thread_title')

    def get_board(self) -> GDO_ForumBoard:
        return self.column('thread_board').get_value()
