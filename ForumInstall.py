from gdo.forum.GDO_ForumBoard import GDO_ForumBoard


class ForumInstall:
    """Install the single root of the forum nested-set tree."""

    @classmethod
    async def on_install(cls):
        if GDO_ForumBoard.table().get_by_aid('1') is None:
            GDO_ForumBoard.blank({
                'board_id': '1',
                'board_title': 'Forum',
                'board_tree_left': '1',
                'board_tree_right': '2',
            }).insert()
