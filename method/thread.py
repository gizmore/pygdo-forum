from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.base.Query import Query
from gdo.base.Render import Mode
from gdo.forum.GDO_ForumPost import GDO_ForumPost
from gdo.forum.GDT_Thread import GDT_Thread
from gdo.table.MethodQueryCards import MethodQueryCards
from gdo.core.GDO_User import GDO_User
from gdo.core.GDT_Container import GDT_Container
from gdo.ui.GDT_Link import GDT_Link
from gdo.ui.GDT_Panel import GDT_Panel
from gdo.forum.ForumAccess import ForumAccess


class thread(ForumAccess, MethodQueryCards):
    """Show a thread's posts as chronological message cards."""

    def gdo_method_hidden(self) -> bool:
        return True

    def gdo_needs_authentication(self) -> bool:
        return False

    def gdo_ordered(self) -> bool:
        return False

    def gdo_searched(self) -> bool:
        return False

    def gdo_filtered(self) -> bool:
        return False

    def gdo_parameters(self) -> list[GDT]:
        return [
            GDT_Thread('id').not_null().positional(False),
        ]

    def get_thread(self):
        return self.param_value('id')

    def gdo_paginate_name(self) -> str:
        return '_p'

    def gdo_has_permission(self, user) -> bool:
        discussion = self.param_value('id', False)
        return bool(discussion and (board := discussion.get_board()) and board.has_permission(user))

    def gdo_table(self) -> GDO:
        return GDO_ForumPost.table()

    def gdo_table_query(self) -> Query:
        return self.gdo_table().select().where(f'post_thread={self.get_thread().get_id()}').order('post_created ASC, post_id ASC')

    def gdo_execute(self) -> GDT:
        result = GDT_Container().vertical().add_fields(
            GDT_Panel().title_raw(self.get_thread().render_name()),
            super().gdo_execute(),
        )
        user = GDO_User.current()
        if user.is_authenticated():
            result.add_field(GDT_Link().href(self.gdo_module().href('reply', f'&thread={self.get_thread().get_id()}')).text('btn_forum_reply'))
        if user.is_staff():
            result.add_field(GDT_Link().href(self.gdo_module().href('thread_crud', f'&id={self.get_thread().get_id()}')).text('btn_edit_thread'))
        if (board := self.get_thread().get_board()) and board.has_permission(user):
            result.add_field(GDT_Link().href(self.gdo_module().href('forum', f'&id={board.get_id()}')).text('btn_thread_board'))
        return result

    def render_gdo(self, post: GDO_ForumPost, mode: Mode) -> str:
        if mode == Mode.render_html:
            return post.render_card()
        if mode in (Mode.render_txt, Mode.render_cli, Mode.render_irc):
            return f"{post.column('post_creator').render(mode)}: {post.render_message(mode)}"
        return super().render_gdo(post, mode)
