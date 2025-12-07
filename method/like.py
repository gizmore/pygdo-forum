from gdo.base.GDO import GDO
from gdo.forum.GDO_ForumPost import GDO_ForumPost
from gdo.forum.GDO_ForumPostLikes import GDO_ForumPostLikes
from gdo.likes.MethodLike import MethodLike


class like(MethodLike):

    def gdo_liked_table(self) -> GDO:
        return GDO_ForumPost().table()

    def gdo_likes_table(self) -> GDO:
        return GDO_ForumPostLikes().table()
