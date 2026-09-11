from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.core.GDT_AutoInc import GDT_AutoInc
from gdo.core.GDT_Object import GDT_Object
from gdo.core.GDT_User import GDT_User
from gdo.date.GDT_Created import GDT_Created
from gdo.date.GDT_Edited import GDT_Edited
from gdo.forum.GDO_ForumThread import GDO_ForumThread
from gdo.message.GDT_Message import GDT_Message
from gdo.ui.GDT_Card import GDT_Card


class GDO_ForumPost(GDO):
    """One authored message in a forum thread."""

    def gdo_columns(self) -> list[GDT]:
        return [
            GDT_AutoInc('post_id'),
            GDT_Object('post_thread').table(GDO_ForumThread.table()).not_null().cascade_delete(),
            GDT_User('post_creator').not_null(),
            GDT_Message('post_message').not_null(),
            GDT_Created('post_created'),
            GDT_Edited('post_edited'),
        ]

    def render_card(self) -> str:
        card = GDT_Card().gdo(self)
        card.get_header().add_fields(
            self.column('post_creator'),
            self.column('post_created'),
        )
        card.get_content().add_field(self.column('post_message'))
        return card.render_html()
