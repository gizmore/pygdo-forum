from gdo.core.GDT_Enum import GDT_Enum


class GDT_ForumSubscription(GDT_Enum):

    NONE = 'none'
    MANUAL = 'manual'
    MINE = 'mine'
    ALL = 'all'

    def __init__(self, name: str):
        super().__init__(name)
        self.not_null()
        self.initial(self.NONE)

    def gdo_choices(self) -> dict:
        return {
            self.NONE: self.NONE,
            self.MANUAL: self.MANUAL,
            self.MINE: self.MINE,
            self.ALL: self.ALL,
        }
