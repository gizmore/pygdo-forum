import os

from gdo.base.Application import Application
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard
from gdo.forum.GDT_ForumBoard import GDT_ForumBoard
from gdo.forum.method.board import board
from gdo.forum.method.boards import boards
from gdo.form.GDT_Form import GDT_Form
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
        self.assertTrue(method.feature_create())
        self.assertEqual('staff', method.gdo_user_permission())

    async def test_install_creates_one_root_board(self):
        reinstall_module('forum')

        root = GDO_ForumBoard.table().get_by_aid('1')
        self.assertEqual('Forum', root.gdo_val('board_title'))
        self.assertEqual((1, 2), root.column('board_tree').get_value())
        self.assertEqual(1, int(GDO_ForumBoard.table().select('COUNT(*)').exec().fetch_val()))
        self.assertEqual(0, root.num_posts())

    async def test_child_board_is_inserted_under_its_parent(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')

        child = GDO_ForumBoard.create_child(root, 'Development')

        self.assertEqual((1, 4), root.column('board_tree').get_value())
        self.assertEqual((2, 3), child.column('board_tree').get_value())

    async def test_board_selector_renders_ascii_tree(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        child = GDO_ForumBoard.create_child(root, 'Development')

        choices = GDT_ForumBoard('board_parent').init_choices()

        self.assertEqual('+-- Forum', choices[root.get_id()])
        self.assertEqual('|  +-- Development', choices[child.get_id()])

    async def test_root_board_parent_selector_is_not_writable(self):
        reinstall_module('forum')
        method = board().input('id', '1')
        method.parameters()
        form = GDT_Form()
        method.gdo_create_form(form)

        self.assertFalse(form.get_field('board_parent').is_writable())

    async def test_child_board_can_move_to_another_parent(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        alpha = GDO_ForumBoard.create_child(root, 'Alpha')
        beta = GDO_ForumBoard.create_child(root, 'Beta')

        alpha.move_to(beta)

        self.assertEqual((1, 6), root.column('board_tree').get_value())
        self.assertEqual((2, 5), beta.column('board_tree').get_value())
        self.assertEqual((3, 4), alpha.column('board_tree').get_value())

    async def test_boards_cards_list_direct_children(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        alpha = GDO_ForumBoard.create_child(root, 'Alpha')
        beta = GDO_ForumBoard.create_child(root, 'Beta')
        GDO_ForumBoard.create_child(alpha, 'Nested')
        method = boards().input('board', root.get_id())
        method.parameters()

        result = method.gdo_table_query().exec().fetch_all()

        self.assertEqual([alpha.get_id(), beta.get_id()], [entry.get_id() for entry in result])
