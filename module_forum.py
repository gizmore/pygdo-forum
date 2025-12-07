from gdo.base.GDO_Module import GDO_Module
from gdo.base.GDT import GDT
from gdo.core.GDO_User import GDO_User
from gdo.core.GDT_UInt import GDT_UInt
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard
from gdo.forum.GDO_ForumPost import GDO_ForumPost
from gdo.forum.GDO_ForumPostLikes import GDO_ForumPostLikes
from gdo.forum.GDO_ForumSubscriptionBoard import GDO_ForumSubscriptionBoard
from gdo.forum.GDO_ForumSubscriptionThread import GDO_ForumSubscriptionThread
from gdo.forum.GDO_ForumThread import GDO_ForumThread
from gdo.forum.GDT_ForumSubscription import GDT_ForumSubscription
from gdo.table.module_table import module_table
from gdo.ui.GDT_Image import GDT_Image
from gdo.ui.GDT_Link import GDT_Link
from gdo.ui.GDT_Page import GDT_Page
from gdo.user.GDT_Level import GDT_Level


class module_forum(GDO_Module):

    def __init__(self):
        super().__init__()
        self._priority = 45

    def gdo_dependencies(self) -> list:
        return [
            'likes',
        ]

    def gdo_classes(self):
        return [
            GDO_ForumBoard,
            GDO_ForumThread,
            GDO_ForumPost,
            GDO_ForumPostLikes,
            GDO_ForumSubscriptionBoard,
            GDO_ForumSubscriptionThread,
        ]

    async def gdo_install(self):
        from gdo.forum.ForumInstall import ForumInstall
        ForumInstall.on_install(self)

    ##########
    # Config #
    ##########
    def gdo_module_config(self) -> list[GDT]:
        return [
            GDT_Image('default_board_image'),
            GDT_UInt('forum_ppp').min(1).max(500),
            GDT_UInt('num_latest').min(1).max(500).initial('10'),
            GDT_Level('post_level').min(0).max(1_000_000).initial('0'),
        ]

    def cfg_posts_per_page(self) -> int:
        return self.get_config_value('forum_ppp') or module_table.instance().cfg_ipp()

    def cfg_default_board_image(self):
        return self.get_config_value('default_board_image')

    def cfg_default_board_image_id(self):
        return self.get_config_val('default_board_image')

    def cfg_post_level(self) -> int:
        return self.get_config_value('post_level')

    ############
    # Settings #
    ############
    def gdo_user_settings(self) -> list[GDT]:
        return [
            GDT_ForumSubscription('forum_subscriptions'),
        ]

    def cfg_subscriptions(self, user: GDO_User = None):
        user = user or GDO_User.current()
        return user.get_setting_val('forum_subscriptions')

    ##########
    # Module #
    ##########
    def gdo_init_sidebar(self, page: 'GDT_Page'):
        page._left_bar.add_field(GDT_Link().href(self.href('boards')).text('link_forum', (GDO_ForumPost.get_num_posts(),)))

