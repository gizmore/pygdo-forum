from gdo.base.Cache import Cache
from gdo.base.GDT import GDT
from gdo.form.GDT_Form import GDT_Form
from gdo.form.MethodForm import MethodForm
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard
from gdo.forum.GDO_ForumPost import GDO_ForumPost
from gdo.forum.GDO_ForumThread import GDO_ForumThread
from gdo.forum.GDT_Board import GDT_Board
from gdo.message.GDT_Message import GDT_Message
from gdo.ui.GDT_Title import GDT_Title


class addthread(MethodForm):
    def gdo_parameters(self) -> list[GDT]:
        return [
            GDT_Board('bid').not_null(),
        ]

    def get_board(self) -> GDO_ForumBoard:
        return self.param_value('bid')

    def gdo_create_form(self, form: GDT_Form) -> None:
        form.add_fields(
            GDT_Title('title').not_null(),
            GDT_Message('message').not_null(),
        )
        super().gdo_create_form(form)

    async def form_submitted(self):
        thread = GDO_ForumThread.blank({
            'thread_board': self.get_board().get_id(),
            'thread_title': self.param_val('title'),
        }).insert()
        post = GDO_ForumPost.blank({
            'post_thread': thread.get_id(),
            'post_message': self.param_val('message'),
        }).insert()
        Cache.remove('forum', 'postcount')
        return self.redirect(post.get_href(), 'forum_add_thread_success')
