from gdo.base.GDT import GDT
from gdo.base.GDO import GDO
from gdo.core.GDT_User import GDT_User
from gdo.forum.GDT_Thread import GDT_Thread


class GDO_ForumSubscriptionThread(GDO):

    def gdo_columns(self) -> list[GDT]:
        return [
            GDT_Thread('fst_thread').primary(),
            GDT_User('fst_user').primary(),
        ]

    