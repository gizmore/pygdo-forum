from gdo.base.GDT import GDT
from gdo.core.GDO_User import GDO_User
from gdo.form.GDT_Form import GDT_Form
from gdo.form.GDT_Submit import GDT_Submit
from gdo.form.MethodForm import MethodForm
from gdo.forum.GDO_ForumPost import GDO_ForumPost
from gdo.forum.GDO_ForumThread import GDO_ForumThread
from gdo.forum.GDT_Board import GDT_Board


class new_thread(MethodForm):
    """Create a thread together with its opening post."""

    def gdo_parameters(self) -> list[GDT]:
        # This accepts the board supplied by the board page's ``New thread``
        # link before the form is built.
        return [GDT_Board('thread_board')]

    def gdo_has_permission(self, user) -> bool:
        board = self.param_value('thread_board', False)
        return not board or board.has_permission(user)

    def gdo_submit_button(self) -> GDT_Submit:
        return GDT_Submit('create').text_raw('Create').calling(self.form_submitted).default_button()

    def gdo_create_form(self, form: GDT_Form) -> None:
        form.add_fields(
            GDT_Board('thread_board').not_null().initial(self.param_val('thread_board', False)),
            GDO_ForumThread.table().column('thread_title'),
            GDO_ForumPost.table().column('post_message'),
        )
        form.actions().add_field(self.gdo_submit_button())

    def form_submitted(self):
        board = self.param_value('thread_board')
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
        self.msg('msg_crud_created', (thread.render_name(),))
        return self.get_form()
