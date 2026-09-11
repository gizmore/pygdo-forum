import os

from gdo.base.Application import Application
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard
from gdo.forum.GDO_ForumPost import GDO_ForumPost
from gdo.forum.GDO_ForumThread import GDO_ForumThread
from gdo.forum.GDT_ForumBoard import GDT_ForumBoard
from gdo.forum.method.board import board
from gdo.forum.method.boards import boards
from gdo.forum.method.forum import forum
from gdo.forum.method.new_thread import new_thread
from gdo.forum.method.thread_crud import thread_crud
from gdo.forum.method.thread import thread
from gdo.forum.method.threads import threads
from gdo.form.GDT_Form import GDT_Form
from gdo.core.connector.Bash import Bash
from gdotest.TestUtil import GDOTestCase, cli_gizmore, reinstall_module


class ForumBoardTest(GDOTestCase):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        Application.init(os.path.dirname(__file__) + '/../../../')
        Application.init_cli()

    def test_board_has_a_nested_set_tree(self):
        columns = GDO_ForumBoard.table().columns()

        self.assertEqual(
            {'board_id', 'board_title', 'board_icon', 'board_permission',
             'board_tree', 'board_tree_left', 'board_tree_right'},
            set(columns),
        )

    def test_board_tree_bounds_are_available_as_a_pair(self):
        board = GDO_ForumBoard.blank({
            'board_title': 'Development',
            'board_tree_left': '1',
            'board_tree_right': '2',
        })

        self.assertEqual((1, 2), board.column('board_tree').get_value())

    def test_thread_and_post_models_have_their_relations(self):
        self.assertEqual(
            {'thread_id', 'thread_board', 'thread_title', 'thread_creator', 'thread_created'},
            set(GDO_ForumThread.table().columns()),
        )
        self.assertEqual(
            {'post_id', 'post_thread', 'post_creator', 'post_message_input',
             'post_message_editor', 'post_created', 'post_edited'},
            set(GDO_ForumPost.table().columns()).intersection({
                'post_id', 'post_thread', 'post_creator', 'post_message_input',
                'post_message_editor', 'post_created', 'post_edited',
            }),
        )

    async def test_threads_list_is_scoped_to_its_board(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        method = threads().input('board', root.get_id())
        method.parameters()

        self.assertFalse(method.gdo_needs_authentication())
        self.assertIn(f'thread_board={root.get_id()}', method.gdo_table_query().build_query())

    async def test_thread_posts_cards_are_scoped_to_the_thread(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        thread_gdo = GDO_ForumThread.blank({
            'thread_board': root.get_id(),
            'thread_title': 'Welcome',
        }).insert()
        method = thread().input('thread', thread_gdo.get_id())
        method.parameters()

        self.assertFalse(method.gdo_needs_authentication())
        self.assertIn(f'post_thread={thread_gdo.get_id()}', method.gdo_table_query().build_query())

    async def test_forum_view_embeds_the_selected_board_threads(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        child = GDO_ForumBoard.create_child(root, 'Development')
        method = forum().input('board', root.get_id())
        method.env_user(cli_gizmore()).env_server(Bash.get_server()).env_session(None)
        method.parameters()

        rendered = await method.gdo_execute()

        self.assertEqual(root.get_id(), method.get_threads().param_value('board').get_id())
        self.assertEqual(root.get_id(), method.get_child_boards().param_value('board').get_id())
        self.assertEqual(3, len(rendered.get_fields()))
        self.assertEqual([child.get_id()], [entry.get_id() for entry in method.get_child_boards().get_table_result()])
        self.assertIn(root.render_name(), rendered.render_html())

    def test_board_crud_only_edits_board_metadata(self):
        method = board()
        fields = method.gdo_form_fields(GDO_ForumBoard.table())

        self.assertEqual(
            ['board_title', 'board_icon', 'board_permission'],
            [field.get_name() for field in fields],
        )
        self.assertTrue(method.feature_create())
        self.assertEqual('staff', method.gdo_user_permission())

    def test_thread_crud_only_edits_thread_content_metadata(self):
        method = thread_crud()

        self.assertEqual(
            ['thread_board', 'thread_title'],
            [field.get_name() for field in method.gdo_form_fields(GDO_ForumThread.table())],
        )
        self.assertTrue(method.feature_create())
        self.assertTrue(method.feature_update())

    async def test_thread_crud_prefills_the_board_from_a_new_thread_link(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        method = thread_crud().input('thread_board', root.get_id())
        method.parameters()

        self.assertEqual(
            root.get_id(),
            method.get_form().get_field('thread_board').get_value().get_id(),
        )

    async def test_new_thread_creates_its_opening_post(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        Application.set_current_user(cli_gizmore())
        method = new_thread().input('thread_board', root.get_id()).input(
            'thread_title', 'Welcome').input(
            'post_message_input', 'This is the opening post.').input(
            'post_message_editor', 'html')
        method.parameters()

        method.form_submitted()

        thread_gdo = GDO_ForumThread.table().get_by_vals({'thread_title': 'Welcome'})
        post = GDO_ForumPost.table().get_by_vals({'post_thread': thread_gdo.get_id()})
        self.assertEqual(root.get_id(), thread_gdo.get_board().get_id())
        self.assertEqual(cli_gizmore().get_id(), post.gdo_val('post_creator'))
        self.assertEqual('This is the opening post.', post.gdo_val('post_message_input'))

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

    async def test_child_board_icon_is_optional_and_persisted(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')

        child = GDO_ForumBoard.create_child(root, 'Development', 'code')

        self.assertEqual('code', child.gdo_val('board_icon'))
        self.assertIsNone(root.gdo_val('board_icon'))

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

    async def test_board_crud_has_labeled_create_edit_delete_actions(self):
        reinstall_module('forum')

        create_form = board().get_form()
        self.assertEqual(['create'], [action.get_name() for action in create_form.actions().get_fields()])
        self.assertEqual(['Create'], [action.render_text() for action in create_form.actions().get_fields()])

        edit_method = board().input('id', '1')
        edit_method.parameters()
        edit_form = edit_method.get_form()
        self.assertEqual(['edit', 'delete'], [action.get_name() for action in edit_form.actions().get_fields()])
        self.assertEqual(['Edit', 'Delete'], [action.render_text() for action in edit_form.actions().get_fields()])

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

    async def test_boards_exposes_actions_for_the_current_board(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        method = boards().input('board', root.get_id())
        method.parameters()

        actions = method.board_actions().get_fields()

        self.assertEqual(['new_board', 'edit_board', 'new_thread'], [action.get_name() for action in actions])
        self.assertIn(f'board_parent.{root.get_id()}', actions[0].render_href())
        self.assertIn(f'id.{root.get_id()}', actions[1].render_href())
        self.assertIn(f'forum.new_thread.thread_board.{root.get_id()}', actions[2].render_href())
