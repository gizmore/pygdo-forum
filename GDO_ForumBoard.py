from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.base.util.href import href
from gdo.core.GDT_AutoInc import GDT_AutoInc
from gdo.core.GDT_Creator import GDT_Creator
from gdo.core.GDT_Object import GDT_Object
from gdo.core.GDT_Permission import GDT_Permission
from gdo.date.GDT_Created import GDT_Created
from gdo.message.GDT_Message import GDT_Message
from gdo.ui.GDT_Card import GDT_Card
from gdo.ui.GDT_Image import GDT_Image
from gdo.ui.GDT_Link import GDT_Link
from gdo.ui.GDT_Title import GDT_Title


class GDO_ForumBoard(GDO):

    def gdo_columns(self) -> list[GDT]:
        return [
            GDT_AutoInc('board_id'),
            GDT_Object('board_parent').table(self),
            GDT_Title('board_title').not_null(),
            GDT_Image('board_image'),
            GDT_Permission('board_permission'),
            GDT_Creator('board_creator'),
            GDT_Created('board_created'),
        ]

    def get_image(self):
        return self.gdo_value('board_image')

    def render_card(self) -> str:
        card = GDT_Card()
        card.get_content().add_field(GDT_Link().href(href('forum', 'board', f'&id={self.get_id()}')).text_raw(self.gdo_val('board_title')))
        if image := self.get_image():
            card.image(image)
        return card.render_card()

    def render_name(self):
        return self.gdo_val('board_title')