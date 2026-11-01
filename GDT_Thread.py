from gdo.core.GDT_ObjectSelect import GDT_ObjectSelect
from gdo.core.GDO_User import GDO_User
from gdo.forum.GDO_ForumThread import GDO_ForumThread


class GDT_Thread(GDT_ObjectSelect):
    """Select one forum discussion thread by title or identifier."""

    def __init__(self, name: str):
        super().__init__(name)
        self.table(GDO_ForumThread.table())

    @staticmethod
    def readable(discussion) -> bool:
        board = discussion.get_board()
        return bool(board and board.has_permission(GDO_User.current()))

    def gdo_choices(self) -> dict:
        return {discussion.get_id(): discussion for discussion in self._table.select().where('thread_deleted IS NULL').nocache().exec()
                if self.readable(discussion)}

    def init_choices(self):
        # Permissions can change while a selector instance remains in use.
        if hasattr(self, '_choices'):
            del self._choices
        return super().init_choices()

    def query_gdos(self, val: str):
        if val.isdigit():
            # Direct routes recheck board access in their methods; preserving
            # ID resolution lets them return a permission error, not a 500.
            return super().query_gdos(val)
        candidates = self._table.select().where(
            f"thread_title LIKE '%{self._table.escape(val)}%' AND thread_deleted IS NULL"
        ).nocache().exec().fetch_all()
        return [discussion for discussion in candidates if self.readable(discussion)]
