from gdo.base.GDO import GDO
from gdo.forum.GDO_ForumPost import GDO_ForumPost
from gdo.likes.GDO_LikeTable import GDO_LikeTable


class GDO_ForumPostLikes(GDO_LikeTable):

    def gdo_liked_table(self) -> GDO:
        return GDO_ForumPost().table()
