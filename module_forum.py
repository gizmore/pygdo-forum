from gdo.base.GDO import GDO
from gdo.base.GDO_Module import GDO_Module
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard


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
