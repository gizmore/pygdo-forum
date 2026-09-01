from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.base.Render import Mode
from gdo.base.Application import Application
from gdo.base.util.href import href
from gdo.forum.GDO_ForumPost import GDO_ForumPost
from gdo.forum.GDO_ForumThread import GDO_ForumThread
from gdo.forum.GDT_Thread import GDT_Thread
from gdo.forum.ForumReadState import ForumReadState
from gdo.table.GDT_Table import TableMode
from gdo.table.MethodQueryTable import MethodQueryTable
from gdo.ui.GDT_Bar import GDT_Bar
from gdo.ui.GDT_Link import GDT_Link
from gdo.ui.GDT_Menu import GDT_Menu


class thread(MethodQueryTable):

    def gdo_searched(self) -> bool:
        return False

    def gdo_table_mode(self) -> TableMode:
        return TableMode.CARDS

    def gdo_parameters(self) -> list[GDT]:
        return [
            GDT_Thread('id').not_null(),
        ]

    def get_thread(self) -> GDO_ForumThread:
        return self.param_value('id')

    def gdo_table(self) -> GDO:
        return GDO_ForumPost.table()

    def render_gdo(self, post: GDO_ForumPost, mode: Mode) -> str:
        creator = post.column('post_creator').render(mode)
        message = post.column('post_message').render(mode)
        return f'{post.get_post_num()}: {creator}: {message}'

    def gdo_execute(self) -> GDT:
        thread = self.get_thread()
        ForumReadState.mark_thread_read(thread, self._env_user)
        bar = GDT_Bar().vertical()
        table = super().gdo_execute()
        if not Application.get_mode().is_html():
            return table
        menu = GDT_Menu()
        menu.add_fields(
            GDT_Link().href(href('forum', 'reply', f'&tid={thread.get_id()}'))
        )
        bar.add_fields(thread, table, menu)
        return bar
