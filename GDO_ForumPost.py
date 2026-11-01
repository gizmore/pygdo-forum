from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.base.Util import module_enabled
from gdo.base.Render import Mode
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
from gdo.message.editor.Editor import Editor
from gdo.core.GDT_Template import GDT_Template


class GDO_ForumPost(WithLikes, GDO):
    """One authored message in a forum thread."""

    def thread_page(self) -> int:
        """Locate this post using the same ordering as the thread view."""
        from gdo.forum.method.thread import thread
        post_id = int(self.get_id())
        table = self.gdo_table_name()
        before = self.table().select('COUNT(*)').where(f'post_thread={int(self.gdo_val("post_thread"))}').where(
            f'post_created < (SELECT post_created FROM {table} WHERE post_id={post_id}) OR '
            f'(post_created = (SELECT post_created FROM {table} WHERE post_id={post_id}) AND post_id<={post_id})'
        ).exec().fetch_val()
        return max(1, (int(before or 1) - 1) // thread().gdo_paginate_size() + 1)

    def gdo_likes_table(self) -> GDO_LikeTable:
        return GDO_ForumLikes.table()

    def render_message(self, mode: Mode) -> str:
        """Render without storing a cache or marking the post edited."""
        message = self.column('post_message')
        return Editor.parse_tree(message.converted_html()).render(mode)

    def gdo_columns(self) -> list[GDT]:
        from gdo.forum.GDO_ForumThread import GDO_ForumThread
        return [
            GDT_AutoInc('post_id'),
            GDT_Object('post_thread').table(GDO_ForumThread.table()).not_null().cascade_delete(),
            GDT_Message('post_message').label('message').not_null(),
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
            'post': self,
            'thread': self.column('post_thread').get_value(),
            'avatar': avatar,
            'creator': creator,
            'created': self.column('post_created'),
            'message_html': self.render_message(Mode.render_html),
            'edited': self.column('post_edited'),
        })
