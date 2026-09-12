from gdo.base.GDO import GDO
from gdo.likes.GDO_LikeTable import GDO_LikeTable
from gdo.likes.WithLikes import WithLikes


class GDO_ForumLikes(GDO_LikeTable):

    def gdo_liked_table(self) -> GDO|WithLikes:
        from gdo.forum.GDO_ForumPost import GDO_ForumPost
        return GDO_ForumPost.table()
