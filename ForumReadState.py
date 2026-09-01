from gdo.core.GDO_User import GDO_User
from gdo.forum.GDO_ForumPost import GDO_ForumPost
from gdo.forum.GDO_ForumThread import GDO_ForumThread
from gdo.forum.GDO_ForumThreadRead import GDO_ForumThreadRead


class ForumReadState:

    @classmethod
    def mark_thread_read(cls, thread: GDO_ForumThread, user: GDO_User):
        last_post = GDO_ForumPost.table().select('MAX(post_id)').where(
            f'post_thread={GDO_ForumPost.table().quote(thread.get_id())}'
        ).exec().fetch_val() or '0'
        return GDO_ForumThreadRead.blank({
            'ftr_thread': thread.get_id(),
            'ftr_user': user.get_id(),
            'ftr_post': last_post,
        }).soft_replace()
