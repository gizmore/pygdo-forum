from gdo.base.GDT import GDT
from gdo.base.util.href import href
from gdo.form.GDT_Form import GDT_Form
from gdo.form.MethodForm import MethodForm
from gdo.forum.ForumSubscriptions import ForumSubscriptions
from gdo.forum.module_forum import module_forum
from gdo.forum.GDO_ForumPost import GDO_ForumPost
from gdo.forum.GDO_ForumThread import GDO_ForumThread
from gdo.forum.GDT_Thread import GDT_Thread
from gdo.message.GDT_Message import GDT_Message


class reply(MethodForm):

    def gdo_needs_level(self) -> int:
        return module_forum.instance().cfg_post_level()

    def gdo_user_type(self) -> str | None:
        return "member,guest"

    def gdo_parameters(self) -> list[GDT]:
        return [
            GDT_Thread('tid').not_null(),
        ]

    def get_thread(self) -> GDO_ForumThread:
        return self.param_value('tid')

    def gdo_create_form(self, form: GDT_Form) -> None:
        form.add_fields(
            GDT_Message('message').not_null(),
        )
        super().gdo_create_form(form)

    def form_submitted(self):
        thread = self.get_thread()
        post = GDO_ForumPost.blank({
            'post_thread': thread.get_id(),
            'post_message': self.param_val('message'),
        }).insert()
        self.send_mails()
        ForumSubscriptions.has_subscribed(post, self._env_user)
        return self.redirect(href('forum', 'thread', f'&p={post.get_page_num()}#post-{post.get_id()}'), 'msg_forum_replied')
    