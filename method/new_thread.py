from gdo.base.GDT import GDT
from gdo.core.GDO_User import GDO_User
from gdo.core.GDT_Container import GDT_Container
from gdo.base.Application import Application
from gdo.form.GDT_CSRF import GDT_CSRF
from gdo.form.GDT_Form import GDT_Form
from gdo.form.GDT_Submit import GDT_Submit
from gdo.form.MethodForm import MethodForm
from gdo.forum.GDO_ForumPost import GDO_ForumPost
from gdo.forum.GDO_ForumThread import GDO_ForumThread
from gdo.forum.GDT_Board import GDT_Board
from gdo.ui.GDT_Link import GDT_Link
from gdo.forum.ForumAccess import ForumAccess, ForumPostForm


class new_thread(ForumAccess, ForumPostForm, MethodForm):
    """Create a thread together with its opening post."""

    def gdo_method_hidden(self) -> bool:
        return True

    def gdo_parameters(self) -> list[GDT]:
        # This accepts the board supplied by the board page's ``New thread``
        # link before the form is built.
        return [GDT_Board('thread_board').visible_to(GDO_User.current())]

    def gdo_has_permission(self, user) -> bool:
        board = self.param_value('thread_board', False)
        return user.is_authenticated() and (not board or (board.has_permission(user) and board.is_thread_allowed()))

    def gdo_submit_button(self) -> GDT_Submit:
        return GDT_Submit('create').text_raw('Create').calling(self.form_submitted).default_button()

    def gdo_create_form(self, form: GDT_Form) -> None:
        form.add_fields(
            GDT_Board('thread_board').visible_to(GDO_User.current()).not_null().initial(self.param_val('thread_board', False)),
            GDO_ForumThread.table().column('thread_title'),
            GDO_ForumPost.table().column('post_message'),
        )
        if Application.IS_HTTP:
            form.add_field(GDT_CSRF())
        form.actions().add_field(self.gdo_submit_button())

    def form_submitted(self):
        board = self.param_value('thread_board')
        if not GDO_User.current().is_authenticated() or not board.has_permission(GDO_User.current()) or not board.is_thread_allowed():
            return self.err('err_permission_required')
        thread = GDO_ForumThread.blank({
            'thread_board': board.get_id(),
            'thread_title': self.param_val('thread_title'),
        }).insert()
        GDO_ForumPost.blank({
            'post_thread': thread.get_id(),
            'post_creator': GDO_User.current().get_id(),
            'post_message_input': self.param_val('post_message_input'),
            'post_message_editor': self.param_val('post_message_editor'),
        }).insert()
        self.msg('msg_forum_thread_created', (thread.render_name(),))
        link = GDT_Link().href(self.gdo_module().href('thread', f'&id={thread.get_id()}')).text('btn_forum_view_thread')
        return GDT_Container().vertical().add_fields(link, self.get_form())
