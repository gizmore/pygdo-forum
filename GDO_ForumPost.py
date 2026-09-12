from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.base.Util import module_enabled
from gdo.core.GDT_AutoInc import GDT_AutoInc
from gdo.core.GDT_Creator import GDT_Creator
from gdo.core.GDT_Editor import GDT_Editor
from gdo.core.GDT_Object import GDT_Object
from gdo.date.GDT_Created import GDT_Created
from gdo.date.GDT_Edited import GDT_Edited
from gdo.forum.GDO_ForumLikes import GDO_ForumLikes
from gdo.likes.GDO_LikeTable import GDO_LikeTable
from gdo.likes.WithLikes import WithLikes
from gdo.message.GDT_Message import GDT_Message
from gdo.core.GDT_Template import GDT_Template


class GDO_ForumPost(WithLikes, GDO):
    """One authored message in a forum thread."""

    def gdo_likes_table(self) -> GDO_LikeTable:
        return GDO_ForumLikes.table()

    def gdo_columns(self) -> list[GDT]:
        from gdo.forum.GDO_ForumThread import GDO_ForumThread
        return [
            GDT_AutoInc('post_id'),
            GDT_Object('post_thread').table(GDO_ForumThread.table()).not_null().cascade_delete(),
            GDT_Message('post_message').not_null(),
            GDT_Created('post_created'),
            GDT_Creator('post_creator'),
            GDT_Edited('post_edited'),
            GDT_Editor('post_editor'),
        ]

    def render_card(self) -> str:
        """Render one forum post with its author beside the message."""
        creator = self.column('post_creator')
        avatar = None
        if module_enabled('avatar'):
            from gdo.avatar.GDT_Avatar import GDT_Avatar
            avatar = GDT_Avatar('post_avatar').for_user(creator.get_value())

        return GDT_Template.python('forum', 'post_card.html', {
            'thread': self.column('post_thread').get_value(),
            'avatar': avatar,
            'creator': creator,
            'created': self.column('post_created'),
            'message': self.column('post_message'),
            'edited': self.column('post_edited'),
        })
