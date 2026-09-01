from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.base.Query import Query
from gdo.base.Render import Mode
from gdo.table.GDT_Table import TableMode
from gdo.table.MethodQueryTable import MethodQueryTable
from gdo.forum.GDO_ForumThread import GDO_ForumThread


class unread(MethodQueryTable):
    """List threads with posts newer than the user's last read post."""

    @classmethod
    def gdo_trigger(cls) -> str:
        return 'forum.unread'

    def gdo_table(self) -> GDO:
        return GDO_ForumThread.table()

    def gdo_table_mode(self) -> TableMode:
        return TableMode.LIST

    def gdo_searched(self) -> bool:
        return False

    def gdo_filtered(self) -> bool:
        return False

    def gdo_ordered(self) -> bool:
        return False

    def gdo_table_query(self) -> Query:
        user_id = self._env_user.get_id()
        return self.gdo_table().select().where(
            'EXISTS ('
            'SELECT 1 FROM gdo_forumpost p '
            'WHERE p.post_thread=thread_id '
            'AND p.post_id > COALESCE(('
            'SELECT r.ftr_post FROM gdo_forumthreadread r '
            f'WHERE r.ftr_thread=thread_id AND r.ftr_user={self.gdo_table().quote(user_id)}'
            '), 0)'
            ')'
        ).order('thread_id DESC')

    def render_gdo(self, thread: GDO_ForumThread, mode: Mode) -> str:
        return f'{thread.get_id()}: {thread.gdo_val("thread_title")}'
