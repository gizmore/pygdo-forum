from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.base.Query import Query
from gdo.forum.GDO_ForumPost import GDO_ForumPost
from gdo.forum.GDT_Thread import GDT_Thread
from gdo.table.MethodQueryCards import MethodQueryCards


class thread(MethodQueryCards):
    """Show a thread's posts as chronological message cards."""

    def gdo_needs_authentication(self) -> bool:
        return False

    def gdo_parameters(self) -> list[GDT]:
        return [GDT_Thread('thread').not_null()]

    def get_thread(self):
        return self.param_value('thread')

    def gdo_has_permission(self, user) -> bool:
        return self.get_thread().get_board().has_permission(user)

    def gdo_table(self) -> GDO:
        return GDO_ForumPost.table()

    def gdo_table_query(self) -> Query:
        return self.gdo_table().select().where(
            f'post_thread={self.get_thread().get_id()}'
        ).order('post_created ASC')
