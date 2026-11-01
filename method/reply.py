from gdo.base.GDT import GDT
from gdo.core.GDO_User import GDO_User
from gdo.core.GDT_Container import GDT_Container
from gdo.base.Application import Application
from gdo.form.GDT_CSRF import GDT_CSRF
from gdo.form.GDT_Form import GDT_Form
from gdo.form.GDT_Submit import GDT_Submit
from gdo.form.MethodForm import MethodForm
from gdo.forum.GDO_ForumPost import GDO_ForumPost
from gdo.forum.GDT_Thread import GDT_Thread
from gdo.ui.GDT_Link import GDT_Link
from gdo.forum.ForumAccess import ForumAccess, ForumPostForm


class reply(ForumAccess, ForumPostForm, MethodForm):
    """Write an authenticated reply on an accessible board."""

    def gdo_parameters(self) -> list[GDT]:
        return [GDT_Thread('thread').not_null().positional(False)]

    def gdo_has_permission(self, user: GDO_User) -> bool:
        thread = self.param_value('thread', False)
        return bool(user.is_authenticated() and thread and (board := thread.get_board()) and board.has_permission(user))

    def gdo_create_form(self, form: GDT_Form) -> None:
        form.add_field(GDO_ForumPost.table().column('post_message'))
        if Application.IS_HTTP:
            form.add_field(GDT_CSRF())
        form.actions().add_field(GDT_Submit('reply').text('btn_forum_reply').calling(self.form_submitted).default_button())

    def form_submitted(self):
        thread = self.param_value('thread')
        if not (board := thread.get_board()) or not board.has_permission(GDO_User.current()):
            return self.err('err_permission_required')
        post = GDO_ForumPost.blank({
            'post_thread': thread.get_id(),
            'post_creator': GDO_User.current().get_id(),
            'post_message_input': self.param_val('post_message_input'),
            'post_message_editor': self.param_val('post_message_editor'),
        }).insert()
        self.msg('msg_forum_reply_created')
        href = self.gdo_module().href('thread', f'&id={thread.get_id()}&_p={post.thread_page()}') + f'#forum-post-{post.get_id()}'
        link = GDT_Link().href(href).text('btn_forum_view_thread')
        return GDT_Container().vertical().add_field(link)
