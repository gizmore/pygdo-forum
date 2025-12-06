from gdo.base.Cache import Cache
from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.base.util.href import href
from gdo.core.GDT_AutoInc import GDT_AutoInc
from gdo.core.GDT_Creator import GDT_Creator
from gdo.date.GDT_Created import GDT_Created
from gdo.forum.GDT_Thread import GDT_Thread
from gdo.message.GDT_Message import GDT_Message
from gdo.table.GDT_PageNum import GDT_PageNum


class GDO_ForumPost(GDO):

    @classmethod
    def get_num_posts(cls) -> int:
        count = Cache.get('forum', 'postcount')
        if count is None:
            count = int(cls.table().select('COUNT(*)').exec().fetch_val())
            Cache.set('forum', 'postcount', count)
        return count

    def gdo_columns(self) -> list[GDT]:
        return [
            GDT_AutoInc('post_id'),
            GDT_Thread('post_thread').not_null(),
            GDT_Message('post_message').not_null(),
            GDT_Created('post_created'),
            GDT_Creator('post_creator'),
        ]

    def get_href(self) -> str:
        return href('forum', 'thread', f'&p={self.get_page_num()}#post-{self.get_id()}')

    def get_post_num(self) -> int:
        return int(GDO_ForumPost.table().select('COUNT(*) + 1').where(f"post_thread={self.gdo_val('post_thread')} AND post_created<'{self.gdo_val('post_created')}'").exec().fetch_val())

    def get_page_num(self) -> int:
        from gdo.forum.module_forum import module_forum
        ppp = module_forum.instance().cfg_posts_per_page()
        pno = self.get_post_num()
        return GDT_PageNum.get_page_num(pno, ppp)

