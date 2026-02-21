from gdo.base.Trans import t
from gdo.core.GDO_File import GDO_File
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard
from gdo.forum.module_forum import module_forum


class ForumInstall():

    @classmethod
    def on_install(cls, module_forum: module_forum):
        if not GDO_ForumBoard.table().get_by_aid('1'):
            GDO_ForumBoard.blank({
                'board_id': '1',
                'board_title': t('forum_root_board'),
            }).insert()
        if not module_forum.cfg_default_board_image():
            file = GDO_File.from_path(module_forum.file_path('img/board.png')).save()
            module_forum.save_config_val('default_board_image', file.get_id())

