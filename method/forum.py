from gdo.base.GDT import GDT
from gdo.core.GDT_Container import GDT_Container
from gdo.forum.GDT_Board import GDT_Board
from gdo.forum.method.boards import boards
from gdo.forum.method.threads import threads
from gdo.ui.GDT_Panel import GDT_Panel
from gdo.base.Method import Method


class forum(Method):
    """Show one forum board and the threads directly inside it."""

    def gdo_needs_authentication(self) -> bool:
        return False

    def gdo_parameters(self) -> list[GDT]:
        return [GDT_Board('board').not_null().initial('1')]

    def get_board(self):
        return self.param_value('board')

    def gdo_has_permission(self, user) -> bool:
        return self.get_board().has_permission(user)

    def get_threads(self) -> threads:
        return threads().env_copy(self).input('board', self.get_board().get_id())

    def get_child_boards(self) -> boards:
        return boards().env_copy(self).input('board', self.get_board().get_id())

    async def gdo_execute(self) -> GDT:
        board = self.get_board()
        return GDT_Container().vertical().add_fields(
            GDT_Panel().title_raw(board.render_name()),
            await self.get_child_boards().execute(),
            await self.get_threads().execute(),
        )
