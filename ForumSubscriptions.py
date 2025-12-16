from gdo.core.GDO_User import GDO_User
from gdo.forum.GDO_ForumPost import GDO_ForumPost


class ForumSubscriptions:

    @staticmethod
    def has_subscribed(post: GDO_ForumPost, user: GDO_User) -> bool:
        return True
