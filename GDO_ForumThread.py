from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.base.Query import Query
from gdo.base.Util import Strings
from gdo.core.GDT_AutoInc import GDT_AutoInc
from gdo.core.GDT_Creator import GDT_Creator
from gdo.core.GDT_Editor import GDT_Editor
from gdo.core.GDT_Object import GDT_Object
from gdo.core.GDT_UInt import GDT_UInt
from gdo.core.GDT_Virtual import GDT_Virtual
from gdo.date.GDT_Created import GDT_Created
from gdo.date.GDT_Edited import GDT_Edited
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard
from gdo.forum.GDO_ForumPost import GDO_ForumPost
from gdo.ui.GDT_Title import GDT_Title


class GDO_ForumThread(GDO):
    """A discussion thread, located directly in one forum board."""

    def gdo_columns(self) -> list[GDT]:
        post_table = GDO_ForumPost.table().gdo_table_name()
        return [
            GDT_AutoInc('thread_id'),
            GDT_Object('thread_board').table(GDO_ForumBoard.table()).not_null().cascade_delete(),
            GDT_Title('thread_title').not_null(),
            GDT_Creator('thread_creator'),
            GDT_Created('thread_created'),
            GDT_Editor('thread_editor'),
            GDT_Edited('thread_edited'),
            GDT_Virtual(GDT_UInt('num_replies')).query(Query().table(post_table).select('COUNT(*)').where('post_thread=thread_id')),
        ]

    def render_name(self):
        return self.gdo_val('thread_title')

    def get_board(self) -> GDO_ForumBoard:
        return self.column('thread_board').get_value()

    def seo_title(self) -> str:
        """Return the stable, human-readable part of this thread's URL."""
        return Strings.seo(self.render_name().lower()) or 'thread'

    def num_posts(self) -> int:
        post_table = GDO_ForumPost.table().gdo_table_name()
        return int(Query().table(post_table).gdo(GDO_ForumPost.table()).select('COUNT(*)').where(
            f'post_thread={self.get_id()}'
        ).exec().fetch_val() or 0)

    def get_last_post(self) -> GDO_ForumPost | None:
        return GDO_ForumPost.table().select().where(
            f'post_thread={self.get_id()}'
        ).order('post_created DESC, post_id DESC').first().exec().fetch_object()
