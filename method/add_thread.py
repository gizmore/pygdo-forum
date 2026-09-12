from gdo.base.GDT import GDT
from gdo.base.Method import Method
from gdo.core.GDO_User import GDO_User
from gdo.core.GDT_RestOfText import GDT_RestOfText
from gdo.forum.GDO_ForumPost import GDO_ForumPost
from gdo.forum.GDO_ForumThread import GDO_ForumThread
from gdo.forum.GDT_Board import GDT_Board
from gdo.ui.GDT_Title import GDT_Title


class add_thread(Method):
    """Create a thread and its opening post from one CLI command."""

    @classmethod
    def gdo_trigger(cls):
        return 'forum.add_thread'

    def gdo_needs_authentication(self) -> bool:
        return True

    def gdo_parameters(self) -> list[GDT]:
        return [
            GDT_Board('board').not_null().positional(False),
            GDT_Title('title').not_null().positional(),
            GDT_RestOfText('message').not_null(),
        ]

    def gdo_has_permission(self, user: GDO_User) -> bool:
        board = self.param_value('board', False)
        return bool(board and board.has_permission(user))

    async def gdo_execute(self):
        board = self.param_value('board')
        thread = GDO_ForumThread.blank({
            'thread_board': board.get_id(),
            'thread_title': self.param_val('title'),
        }).insert()
        GDO_ForumPost.blank({
            'post_thread': thread.get_id(),
            'post_creator': GDO_User.current().get_id(),
            'post_message_input': self.param_val('message'),
            'post_message_editor': 'html',
        }).insert()
        return self.msg('msg_crud_created', (thread.render_name(),))
