from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.core.GDO_User import GDO_User
from gdo.core.GDT_AutoInc import GDT_AutoInc
from gdo.core.GDT_Creator import GDT_Creator
from gdo.date.GDT_Created import GDT_Created
from gdo.forum.GDT_Board import GDT_Board
from gdo.ui.GDT_Title import GDT_Title


class GDO_ForumThread(GDO):

    def gdo_columns(self) -> list[GDT]:
        return [
            GDT_AutoInc('thread_id'),
            GDT_Board('thread_board').not_null(),
            GDT_Title('thread_title').not_null(),
            GDT_Creator('thread_creator').not_null(),
            GDT_Created('thread_created').not_null(),
        ]

    def get_creator(self) -> GDO_User:
        return self.gdo_value('thread_creator')

