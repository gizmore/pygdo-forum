from gdo.base.GDO import GDO
from gdo.base.GDO_Module import GDO_Module
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard
from gdo.ui.GDT_Link import GDT_Link

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gdo.ui.GDT_Page import GDT_Page


class module_forum(GDO_Module):
    """The deliberately small foundation for the rebuilt forum."""

    def __init__(self):
        super().__init__()
        self._priority = 45

    def gdo_classes(self) -> list[type[GDO]]:
        return [GDO_ForumBoard]

    async def gdo_install(self):
        from gdo.forum.ForumInstall import ForumInstall
        await ForumInstall.on_install()

    def gdo_init_sidebar(self, page: 'GDT_Page'):
        if root := GDO_ForumBoard.table().get_by_aid('1'):
            page._left_bar.add_field(
                GDT_Link().href(self.href('board', '&id=1')).
                text_raw(root.render_name()).
                attr('title', f'{root.num_posts()} Posts')
            )
