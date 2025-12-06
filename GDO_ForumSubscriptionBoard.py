from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.core.GDT_User import GDT_User
from gdo.forum.GDT_Board import GDT_Board


class GDO_ForumSubscriptionBoard(GDO):

    def gdo_columns(self) -> list[GDT]:
        return [
            GDT_Board('fsb_board').primary(),
            GDT_User('fsb_user').primary(),
        ]

