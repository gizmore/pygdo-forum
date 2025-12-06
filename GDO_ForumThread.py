from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.base.Util import html
from gdo.core.GDO_User import GDO_User
from gdo.core.GDT_AutoInc import GDT_AutoInc
from gdo.core.GDT_Creator import GDT_Creator
from gdo.core.GDT_UInt import GDT_UInt
from gdo.core.GDT_Virtual import GDT_Virtual
from gdo.date.GDT_Created import GDT_Created
from gdo.forum.GDT_Board import GDT_Board
from gdo.ui.GDT_Title import GDT_Title


class GDO_ForumThread(GDO):

    def gdo_columns(self) -> list[GDT]:
        from gdo.forum.GDO_ForumPost import GDO_ForumPost
        return [
            GDT_AutoInc('thread_id'),
            GDT_Board('thread_board').not_null().label('board'),
            GDT_Title('thread_title').not_null().label('title'),
            GDT_UInt('thread_views').not_null().initial('0').label('views'),
            GDT_Creator('thread_creator').not_null().label('creator'),
            GDT_Created('thread_created').not_null().label('created'),
            GDT_Virtual(GDT_UInt('thread_postcount').label('postcount')).query(GDO_ForumPost.table().select('COUNT(*)').where('post_thread=thread_id'))
        ]

    def get_creator(self) -> GDO_User:
        return self.gdo_value('thread_creator')

    def render_list(self):
        title = html(self.gdo_value('thread_title'))
        count = self.gdo_value('thread_postcount')
        created = self.column('thread_created').render_txt()
        creator = self.column('thread_creator').render_list()
        return f"{title} ({count}) - {creator} - {created}"
