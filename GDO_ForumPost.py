from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
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
from gdo.ui.GDT_Card import GDT_Card


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
        card = GDT_Card().gdo(self)
        card.get_header().add_fields(
            self.column('post_creator'),
            self.column('post_created'),
        )
        card.get_content().add_field(self.column('post_message'))
        return card.render_html()
