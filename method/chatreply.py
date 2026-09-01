from gdo.base.GDT import GDT
from gdo.base.Method import Method
from gdo.core.GDT_RestOfText import GDT_RestOfText
from gdo.forum.GDO_ForumPost import GDO_ForumPost
from gdo.forum.GDT_Thread import GDT_Thread


class chatreply(Method):
    """Post a short reply from any text connector."""

    @classmethod
    def gdo_trigger(cls) -> str:
        return 'forum.reply'

    def gdo_parameters(self) -> list[GDT]:
        return [
            GDT_Thread('id').not_null(),
            GDT_RestOfText('text').not_null(),
        ]

    def gdo_execute(self) -> GDT:
        thread = self.param_value('id')
        post = GDO_ForumPost.blank({
            'post_thread': thread.get_id(),
            'post_message_input': self.param_val('text'),
        }).insert()
        return self.reply('msg_forum_replied', (post.get_id(),))
