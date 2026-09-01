from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.core.GDT_User import GDT_User
from gdo.core.GDT_UInt import GDT_UInt
from gdo.forum.GDT_Thread import GDT_Thread


class GDO_ForumThreadRead(GDO):
    """The newest post a user has seen in one forum thread."""

    def gdo_columns(self) -> list[GDT]:
        return [
            GDT_Thread('ftr_thread').primary(),
            GDT_User('ftr_user').primary(),
            GDT_UInt('ftr_post').not_null().initial('0'),
        ]
