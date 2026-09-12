from gdo.base.GDT import GDT
from gdo.core.GDT_Container import GDT_Container
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard
from gdo.forum.GDT_Board import GDT_Board
from gdo.forum.method.threads import threads
from gdo.base.Method import Method
from gdo.ui.GDT_Panel import GDT_Panel


class board(Method):
    """Public board route: ``forum.board.<name>.threads.html``."""

    def gdo_needs_authentication(self) -> bool:
        return False

    def gdo_parameters(self) -> list[GDT]:
        return [
            GDT_Board('board').not_null().positional(),
        ]

    def get_board(self) -> GDO_ForumBoard:
        return self.param_value('board')

    def gdo_has_permission(self, user) -> bool:
        return self.get_board().has_permission(user)

    async def gdo_execute(self) -> GDT:
        current = self.get_board()
        listing = threads().env_copy(self).input('board', current.get_id())
        return GDT_Container().vertical().add_fields(
            GDT_Panel().title_raw(current.render_name()),
            await listing.execute(),
        )
