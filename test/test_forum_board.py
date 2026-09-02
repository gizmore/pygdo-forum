import os

from gdo.base.Application import Application
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard
from gdo.forum.method.board import board
from gdotest.TestUtil import GDOTestCase, reinstall_module


class ForumBoardTest(GDOTestCase):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        Application.init(os.path.dirname(__file__) + '/../../../')
        Application.init_cli()

    def test_board_has_a_nested_set_tree(self):
        columns = GDO_ForumBoard.table().columns()

        self.assertEqual(
            {'board_id', 'board_title', 'board_tree', 'board_tree_left', 'board_tree_right'},
            set(columns),
        )

    def test_board_tree_bounds_are_available_as_a_pair(self):
        board = GDO_ForumBoard.blank({
            'board_title': 'Development',
            'board_tree_left': '1',
            'board_tree_right': '2',
        })

        self.assertEqual((1, 2), board.column('board_tree').get_value())

    def test_board_crud_only_edits_board_metadata(self):
        method = board()
        fields = method.gdo_form_fields(GDO_ForumBoard.table())

        self.assertEqual(['board_title'], [field.get_name() for field in fields])
        self.assertFalse(method.feature_create())
        self.assertEqual('staff', method.gdo_user_permission())

    async def test_install_creates_one_root_board(self):
        reinstall_module('forum')

        root = GDO_ForumBoard.table().get_by_aid('1')
        self.assertEqual('Forum', root.gdo_val('board_title'))
        self.assertEqual((1, 2), root.column('board_tree').get_value())
        self.assertEqual(1, int(GDO_ForumBoard.table().select('COUNT(*)').exec().fetch_val()))
