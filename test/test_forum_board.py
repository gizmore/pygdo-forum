import os
from unittest.mock import MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Database import Database
from gdo.base.Exceptions import GDODBException, GDOError
from gdo.base.ParseArgs import ParseArgs
from gdo.base.Render import Mode
from gdo.base.WithPermissionCheck import WithPermissionCheck
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard
from gdo.forum.GDO_ForumPost import GDO_ForumPost
from gdo.forum.GDO_ForumLikes import GDO_ForumLikes
from gdo.forum.GDO_ForumThread import GDO_ForumThread
from gdo.forum.ForumInstall import ForumInstall
from gdo.forum.GDT_ForumBoard import GDT_ForumBoard
from gdo.forum.GDT_Thread import GDT_Thread
from gdo.forum.module_forum import module_forum
from gdo.forum.method.board import board
from gdo.forum.method.board_crud import board_crud
from gdo.forum.method.boards import boards
from gdo.forum.method.forum import forum
from gdo.forum.method.new_thread import new_thread
from gdo.forum.method.add_thread import add_thread
from gdo.forum.method.reply import reply
from gdo.forum.method.rss import rss, xml_text
from gdo.forum.method.thread_crud import thread_crud
from gdo.forum.method.thread import thread
from gdo.forum.method.threads import threads
from gdo.form.GDT_Form import GDT_Form
from gdo.form.GDT_CSRF import GDT_CSRF
from gdo.form.MethodCrud import MethodCrud
from gdo.core.connector.Bash import Bash
from gdo.ui.GDT_Button import GDT_Button
from gdo.ui.GDT_Link import GDT_Link
from gdotest.TestUtil import GDOTestCase, WebPlug, cli_gizmore, install_module, reinstall_module, text_plug, web_plug
from gdo.core.GDO_Session import GDO_Session
from gdo.core.GDO_User import GDO_User
from gdo.core.GDO_Permission import GDO_Permission
from gdo.core.GDO_UserPermission import GDO_UserPermission


def strict_csrf(field, value):
    """Exercise real CSRF validation without disabling test DB isolation."""
    with patch.object(Application, 'is_unit_test', return_value=False):
        return _csrf_validate(field, value)


_csrf_validate = GDT_CSRF.validate


class ForumBoardTest(GDOTestCase):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        Application.init(os.path.dirname(__file__) + '/../../../')
        Application.init_cli()

    def test_link_nofollow_helper_adds_and_removes_the_relation(self):
        install_module('icon_fa')
        link = GDT_Link().href('/next').nofollow()
        self.assertEqual('nofollow', link.get_attrs()['rel'])
        self.assertIn('rel="nofollow"', link.text_raw('Next').render_html())
        self.assertNotIn('rel', GDT_Link().nofollow(False).get_attrs())

    def test_link_cells_are_full_click_targets(self):
        self.assertEqual('full-click-column', GDT_Link().html_cell_class())

    def test_board_has_a_nested_set_tree(self):
        columns = GDO_ForumBoard.table().columns()

        self.assertEqual(
            {'board_id', 'board_name', 'board_title', 'board_icon', 'board_permission',
             'board_threads_allowed',
             'board_tree', 'board_tree_left', 'board_tree_right',
             'last_post_date', 'num_threads'},
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
            {'thread_id', 'thread_board', 'thread_title', 'thread_creator', 'thread_created',
             'thread_editor', 'thread_edited', 'thread_deleted', 'num_replies'},
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

    async def test_child_board_list_omits_inaccessible_boards(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        public = GDO_ForumBoard.create_child(root, 'Visible child')
        private = GDO_ForumBoard.create_child(root, 'Private child')
        method = boards().input('board', root.get_id())
        method.parameters()
        with patch.object(GDO_ForumBoard, 'has_permission', lambda board, user: board.get_id() != private.get_id()):
            rows = list(method.gdo_table_query().exec())
        self.assertIn(public.get_id(), [row.get_id() for row in rows])
        self.assertNotIn(private.get_id(), [row.get_id() for row in rows])

    async def test_child_board_links_to_parent_only_when_readable(self):
        reinstall_module('forum')
        install_module('icon_fa')
        root = GDO_ForumBoard.table().get_by_aid('1')
        child = GDO_ForumBoard.create_child(root, 'Navigation child')
        path = f'forum.forum.id.{child.get_id()}.html'
        with patch.object(GDO_ForumBoard, 'has_permission', return_value=True):
            self.assertIn('Parent board', web_plug(path).exec())
        with patch.object(GDO_ForumBoard, 'has_permission', lambda board, user: board.get_id() == child.get_id()):
            page = web_plug(path).exec()
            self.assertNotIn('Parent board', page)

    async def test_thread_creation_selector_hides_inaccessible_boards(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        private = GDO_ForumBoard.create_child(root, 'Private selection')
        viewer = cli_gizmore()
        with patch.object(GDO_ForumBoard, 'has_permission', lambda board, user: board.get_id() != private.get_id()):
            selector = GDT_ForumBoard('board').visible_to(viewer)
            self.assertNotIn(private.get_id(), selector.gdo_choices())
            self.assertIsNone(selector.to_value(private.gdo_val('board_name')))

    async def test_board_selectors_recheck_permissions_after_database_change(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        child = GDO_ForumBoard.create_child(root, 'Permission changes')
        cached = GDO_ForumBoard.table().get_by_aid(child.get_id())
        self.assertIsNone(cached.gdo_val('board_permission'))
        staff = GDO_Permission.table().get_by_vals({'perm_name': 'staff'})
        Application.db().query(f'UPDATE gdo_forumboard SET board_permission={int(staff.get_id())} WHERE board_id={int(child.get_id())}')
        with patch.object(GDO_ForumBoard, 'has_permission', lambda board, user: board.gdo_val('board_permission') is None):
            selector = GDT_ForumBoard('board').visible_to(cli_gizmore())
            self.assertNotIn(child.get_id(), selector.gdo_choices())
            self.assertIsNone(selector.to_value(child.gdo_val('board_name')))
            method = boards().input('board', root.get_id())
            method.parameters()
            self.assertNotIn(child.get_id(), [row.get_id() for row in method.gdo_table_query().exec()])

    async def test_board_selector_refreshes_choices_after_access_changes(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        child = GDO_ForumBoard.create_child(root, 'Revocable board')
        selector = GDT_ForumBoard('board').visible_to(cli_gizmore())
        with patch.object(GDO_ForumBoard, 'has_permission', return_value=True):
            self.assertIn(child.get_id(), selector.init_choices())
        with patch.object(GDO_ForumBoard, 'has_permission', lambda board, user: board.get_id() != child.get_id()):
            self.assertNotIn(child.get_id(), selector.init_choices())
            self.assertIsNone(selector.to_value(child.get_id()))
            self.assertIsNone(selector.to_value(child.gdo_val('board_name')))

    async def test_cached_board_rechecks_permission_for_direct_access(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        child = GDO_ForumBoard.create_child(root, 'Access change')
        cached = GDO_ForumBoard.table().get_by_aid(child.get_id())
        user = cli_gizmore()
        self.assertTrue(cached.has_permission(user))
        staff = GDO_Permission.table().get_by_vals({'perm_name': 'staff'})
        Application.db().query(f'UPDATE gdo_forumboard SET board_permission={int(staff.get_id())} WHERE board_id={int(child.get_id())}')
        with patch.object(GDO_Permission, 'has_permission', return_value=False):
            self.assertFalse(cached.has_permission(user))

    async def test_cached_board_rechecks_thread_creation_setting(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        self.assertTrue(root.is_thread_allowed())
        Application.db().query(f'UPDATE gdo_forumboard SET board_threads_allowed=0 WHERE board_id={int(root.get_id())}')
        self.assertFalse(root.is_thread_allowed())

    async def test_thread_access_uses_current_board_after_move(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        private = GDO_ForumBoard.create_child(root, 'Destination')
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Moved'}).insert()
        user = cli_gizmore()
        method = thread().input('id', discussion.get_id())
        method.parameters()
        with patch.object(GDO_ForumBoard, 'has_permission', lambda board, viewer: board.get_id() == root.get_id()):
            self.assertTrue(method.gdo_has_permission(user))
            Application.db().query(f'UPDATE gdo_forumthread SET thread_board={int(private.get_id())} WHERE thread_id={int(discussion.get_id())}')
            self.assertFalse(method.gdo_has_permission(user))

    async def test_direct_web_routes_recheck_board_permission(self):
        reinstall_module('forum')
        install_module('icon_fa')
        root = GDO_ForumBoard.table().get_by_aid('1')
        child = GDO_ForumBoard.create_child(root, 'Restricted web board')
        discussion = GDO_ForumThread.blank({'thread_board': child.get_id(), 'thread_title': 'Restricted web thread'}).insert()
        GDO_ForumPost.blank({'post_thread': discussion.get_id(), 'post_creator': cli_gizmore().get_id(),
                             'post_message_input': 'Restricted web content', 'post_message_editor': 'html'}).insert()
        GDO_ForumBoard.table().get_by_aid(child.get_id())  # Populate the old object cache.
        staff = GDO_Permission.table().get_by_vals({'perm_name': 'staff'})
        previous = WebPlug.COOKIES.copy()
        try:
            WebPlug.COOKIES = {'GDO': GDO_Session.for_user(cli_gizmore()).cookie_value()}
            paths = (f'forum.forum.id.{child.get_id()}.html', f'forum.thread.id.{discussion.get_id()}.html')
            self.assertIn('Restricted web board', web_plug(paths[0]).exec())
            self.assertIn('Restricted web content', web_plug(paths[1]).exec())
            Application.db().query(f'UPDATE gdo_forumboard SET board_permission={int(staff.get_id())} WHERE board_id={int(child.get_id())}')
            with patch.object(GDO_Permission, 'has_permission', return_value=False):
                for path in paths:
                    page = web_plug(path).exec()
                    self.assertNotIn('Traceback (most recent call last)', page)
                    self.assertIn('You are not allowed to access this method.', page)
                    self.assertNotIn('Restricted web board', page)
                    self.assertNotIn('Restricted web thread', page)
                    self.assertNotIn('Restricted web content', page)
        finally:
            WebPlug.COOKIES = previous

    async def test_thread_posts_cards_are_scoped_to_the_thread(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        thread_gdo = GDO_ForumThread.blank({
            'thread_board': root.get_id(),
            'thread_title': 'Welcome',
        }).insert()
        method = thread().input('id', thread_gdo.get_id())
        method.parameters()

        self.assertFalse(method.gdo_needs_authentication())
        self.assertIn(f'post_thread={thread_gdo.get_id()}', method.gdo_table_query().build_query())

    async def test_thread_text_output_contains_the_post_message(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Text thread'}).insert()
        post = GDO_ForumPost.blank({'post_thread': discussion.get_id(), 'post_creator': cli_gizmore().get_id(),
                                    'post_message_input': 'Hello from the forum', 'post_message_editor': 'html'}).insert()
        for mode in (Mode.render_txt, Mode.render_cli, Mode.render_irc):
            self.assertIn('Hello from the forum', thread().render_gdo(post, mode))

    async def test_chat_lists_show_object_ids_not_row_numbers(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        child = GDO_ForumBoard.create_child(root, 'Listable board')
        discussion = GDO_ForumThread.blank({'thread_board': child.get_id(), 'thread_title': 'Listable thread'}).insert()
        for mode in (Mode.render_txt, Mode.render_cli, Mode.render_irc):
            self.assertEqual(f'{child.get_id()}-Listable board', boards().render_gdo(child, mode))
            self.assertEqual(f'{discussion.get_id()}-Listable thread', threads().render_gdo(discussion, mode))
        with patch.object(Application, 'IS_HTTP', False):
            output = text_plug(Mode.render_cli, '$forum.boards --board=forum', cli_gizmore())
        self.assertIn(f'{child.get_id()}-Listable board', output)

    async def test_post_card_escapes_titles_and_purifies_message_html(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': '<script>alert(1)</script>'}).insert()
        post = GDO_ForumPost.blank({'post_thread': discussion.get_id(), 'post_creator': cli_gizmore().get_id(),
                                    'post_message_input': '<b>hello</b><script>alert(2)</script>', 'post_message_editor': 'html'}).insert()
        card = post.render_card()
        self.assertNotIn('<script>', card)
        self.assertIn('&lt;script&gt;', card)
        self.assertIn('hello', card)

    async def test_reply_count_excludes_the_opening_post(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Count replies'}).insert()
        def count():
            row = GDO_ForumThread.table().select().where(f'thread_id={discussion.get_id()}').exec().fetch_object()
            return row.gdo_value('num_replies')
        self.assertEqual(0, count())
        for index in range(3):
            GDO_ForumPost.blank({'post_thread': discussion.get_id(), 'post_creator': cli_gizmore().get_id(),
                                 'post_message_input': f'Post {index}', 'post_message_editor': 'html'}).insert()
            self.assertEqual(index, count())

    async def test_board_reply_count_ignores_empty_legacy_threads(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Empty legacy thread'}).insert()
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Active thread'}).insert()
        for message in ('Opening', 'Reply'):
            GDO_ForumPost.blank({'post_thread': discussion.get_id(), 'post_creator': cli_gizmore().get_id(),
                                 'post_message_input': message, 'post_message_editor': 'html'}).insert()
        self.assertEqual(2, root.num_posts())
        self.assertEqual(1, root.num_replies())

    async def test_board_virtual_statistics_count_direct_threads_and_latest_post(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        child = GDO_ForumBoard.create_child(root, 'Statistics child')
        discussion = GDO_ForumThread.blank({'thread_board': child.get_id(), 'thread_title': 'Child topic'}).insert()
        post = GDO_ForumPost.blank({'post_thread': discussion.get_id(), 'post_creator': cli_gizmore().get_id(),
                                   'post_message_input': 'A post', 'post_message_editor': 'html'}).insert()
        def fresh(board):
            return GDO_ForumBoard.table().select().where(f'board_id={board.get_id()}').nocache().exec().fetch_object()
        root_row, child_row = fresh(root), fresh(child)
        self.assertEqual(0, root_row.gdo_value('num_threads'))
        self.assertEqual(1, child_row.gdo_value('num_threads'))
        self.assertTrue(post.gdo_val('post_created').startswith(child_row.gdo_val('last_post_date')))

    async def test_rss_filters_before_limiting_and_identifies_each_post(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        hidden = GDO_ForumBoard.create_child(root, 'Hidden feed board')
        public_thread = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Public feed'}).insert()
        hidden_thread = GDO_ForumThread.blank({'thread_board': hidden.get_id(), 'thread_title': 'Private feed'}).insert()
        for index in range(2):
            GDO_ForumPost.blank({'post_thread': public_thread.get_id(), 'post_creator': cli_gizmore().get_id(),
                                 'post_message_input': f'Public {index}', 'post_message_editor': 'html'}).insert()
        for index in range(51):
            GDO_ForumPost.blank({'post_thread': hidden_thread.get_id(), 'post_creator': cli_gizmore().get_id(),
                                 'post_message_input': f'Hidden {index}', 'post_message_editor': 'html'}).insert()
        method = rss()
        method._env_user = cli_gizmore()
        with patch.object(GDO_ForumBoard, 'has_permission', lambda board, user: board.get_id() == root.get_id()), \
             patch.object(thread, 'gdo_paginate_size', return_value=1):
            xml = method.gdo_execute().get_val()
        import xml.etree.ElementTree as ET
        items = ET.fromstring(xml).findall('./channel/item')
        self.assertNotIn('Hidden ', xml)
        self.assertEqual(2, len(items))
        self.assertTrue(all(item.findtext('title') == 'Public feed' for item in items))
        self.assertEqual({'Public 0', 'Public 1'}, {item.findtext('description') for item in items})
        self.assertEqual(2, len({item.findtext('guid') for item in items}))
        self.assertIn('_p=2', items[0].findtext('link'))
        self.assertIn('#forum-post-', items[0].findtext('link'))
        self.assertIn('_p=1', items[1].findtext('link'))
        with patch.object(GDO_ForumBoard, 'has_permission', lambda board, user: board.get_id() == root.get_id()), \
             patch.object(thread, 'gdo_paginate_size', return_value=10):
            other_items = ET.fromstring(method.gdo_execute().get_val()).findall('./channel/item')
        self.assertEqual([item.findtext('guid') for item in items], [item.findtext('guid') for item in other_items])

    def test_rss_xml_text_escapes_markup_and_discards_invalid_controls(self):
        import xml.etree.ElementTree as ET
        xml = f'<description>{xml_text("A <tag> & B" + chr(1))}</description>'
        self.assertEqual('A <tag> & B', ET.fromstring(xml).text)

    async def test_rss_post_body_is_plain_text_not_executable_markup(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Feed safety'}).insert()
        GDO_ForumPost.blank({'post_thread': discussion.get_id(), 'post_creator': cli_gizmore().get_id(),
                             'post_message_input': '<b>Hello</b><script>alert(1)</script>',
                             'post_message_editor': 'html'}).insert()
        import xml.etree.ElementTree as ET
        feed = rss().env_user(cli_gizmore()).gdo_execute().get_val()
        description = ET.fromstring(feed).find('./channel/item/description')
        self.assertIsNotNone(description)
        self.assertEqual([], list(description))
        self.assertIn('Hello', description.text)
        self.assertNotIn('<script>', feed)

    async def test_rss_does_not_write_render_cache_or_edit_timestamp(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Read only feed'}).insert()
        post = GDO_ForumPost.blank({'post_thread': discussion.get_id(), 'post_creator': cli_gizmore().get_id(),
                                    'post_message_input': 'Fresh feed content', 'post_message_editor': 'html'}).insert()
        output_key = post.column('post_message').get_output_gdt_key(Mode.render_txt)
        def state():
            return GDO_ForumPost.table().select(f'{output_key}, post_edited').where(
                f'post_id={int(post.get_id())}').nocache().exec().fetch_assoc()
        before = state()
        self.assertIsNone(before['post_edited'])
        self.assertFalse(before[output_key])
        feed = rss().env_user(cli_gizmore()).gdo_execute().get_val()
        self.assertIn('Fresh feed content', feed)
        self.assertEqual(before, state())

    async def test_thread_views_do_not_mark_posts_edited(self):
        reinstall_module('forum')
        install_module('icon_fa')
        root = GDO_ForumBoard.table().get_by_aid('1')
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Read-only thread'}).insert()
        post = GDO_ForumPost.blank({'post_thread': discussion.get_id(), 'post_creator': cli_gizmore().get_id(),
                                    'post_message_input': 'Unchanged content', 'post_message_editor': 'html'}).insert()
        def state():
            return GDO_ForumPost.table().select().where(
                f'post_id={int(post.get_id())}').nocache().exec().fetch_object()
        before = state()
        self.assertIsNone(before.gdo_val('post_edited'))
        page = web_plug(f'forum.thread.id.{discussion.get_id()}.html').exec()
        self.assertIn('Unchanged content', page)
        self.assertIn('Unchanged content', thread().render_gdo(post, Mode.render_cli))
        after = state()
        self.assertIsNone(after.gdo_val('post_edited'))
        for mode in (Mode.render_html, Mode.render_cli):
            key = post.column('post_message').get_output_gdt_key(mode)
            self.assertEqual(before.gdo_val(key), after.gdo_val(key))

    async def test_rss_web_route_returns_xml_content_type(self):
        reinstall_module('forum')
        old_cookies = WebPlug.COOKIES.copy()
        try:
            WebPlug.COOKIES = {}
            request = web_plug('forum.rss.rss')
            payload = request.exec()
            import xml.etree.ElementTree as ET
            self.assertEqual('rss', ET.fromstring(payload).tag)
            self.assertTrue(any(name.lower() == 'content-type' and value.startswith('application/rss+xml')
                                for name, value in request._headers))
        finally:
            WebPlug.COOKIES = old_cookies

    async def test_invalid_board_web_routes_do_not_return_server_errors(self):
        reinstall_module('forum')
        install_module('icon_fa')
        paths = ('forum.forum.id.999999.html', 'forum.board.not-a-board.html',
                 'forum.boards.board.999999.html', 'forum.threads.board.999999.html')
        for path in paths:
            with self.subTest(path=path):
                page = web_plug(path).exec()
                self.assertNotIn('Traceback (most recent call last)', page[:10000])
                self.assertNotIn('<title>Server Error</title>', page[:1000])

    async def test_invalid_thread_and_reply_routes_do_not_return_server_errors(self):
        reinstall_module('forum')
        install_module('icon_fa')
        previous = WebPlug.COOKIES.copy()
        try:
            WebPlug.COOKIES = {'GDO': GDO_Session.for_user(cli_gizmore()).cookie_value()}
            for path in ('forum.thread.html', 'forum.thread.id.999999.html', 'forum.thread.html?id=not-a-thread',
                         'forum.reply.html', 'forum.reply.thread.999999.html', 'forum.reply.html?thread=not-a-thread'):
                with self.subTest(path=path):
                    page = web_plug(path).exec()
                    self.assertNotIn('<title>Server Error</title>', page[:1000])
                    self.assertNotIn('Traceback (most recent call last)', page[:10000])
        finally:
            WebPlug.COOKIES = previous

    async def test_thread_list_links_title_and_last_post_to_the_right_pages(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        thread_gdo = GDO_ForumThread.blank({
            'thread_board': root.get_id(),
            'thread_title': 'Welcome to PyGDO!',
        }).insert()
        for message in ('Opening post.', 'A reply.'):
            GDO_ForumPost.blank({
                'post_thread': thread_gdo.get_id(),
                'post_creator': cli_gizmore().get_id(),
                'post_message_input': message,
                'post_message_editor': 'html',
            }).insert()

        method = threads().input('board', root.get_id())
        method.parameters()
        method.gdo_paginate_size = lambda: 100
        title, _created, replies, last_post, _creator = method.gdo_table_headers()
        title_html = method.render_thread_title(title, thread_gdo)
        with patch.object(thread, 'gdo_paginate_size', return_value=1):
            last_post_html = method.render_last_post_date(last_post, thread_gdo)

        title_href = f'/forum.thread.title.welcome_to_pygdo.id.{thread_gdo.get_id()}.html?_p=1'
        last_post_href = f'/forum.thread.title.welcome_to_pygdo.id.{thread_gdo.get_id()}.html?_p=2'
        self.assertIn(title_href, title_html)
        self.assertIn(last_post_href, last_post_html)
        self.assertIn(title_href, last_post_html)
        self.assertIn('firstpost', last_post_html)
        self.assertIn('lastpost', last_post_html)
        self.assertIn(f'#forum-post-{thread_gdo.get_last_post().get_id()}', last_post_html)
        self.assertIn('1', method.render_replies(replies, thread_gdo))

        args = ParseArgs()
        args.add_path_vars(title_href.split('?', 1)[0])
        args.add_get_vars({'_p': ['1']})
        target = args.get_method()
        target.parameters()
        self.assertEqual(thread_gdo.get_id(), target.param_value('id').get_id())
        self.assertEqual(1, target.param_value('_p'))

    async def test_forum_view_embeds_the_selected_board_threads(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        child = GDO_ForumBoard.create_child(root, 'Development')
        method = forum().input('id', root.get_id())
        method.env_user(cli_gizmore()).env_server(Bash.get_server()).env_session(None)
        method.parameters()

        rendered = await method.gdo_execute()

        self.assertEqual(root.get_id(), method.get_threads().param_value('board').get_id())
        self.assertEqual(root.get_id(), method.get_child_boards().param_value('board').get_id())
        self.assertEqual(4, len(rendered.get_fields()))
        self.assertIn('forum.rss.rss', rendered.get_fields()[-1].render_href())
        self.assertEqual([child.get_id()], [entry.get_id() for entry in method.get_child_boards().get_table_result()])
        self.assertIn(root.render_name(), rendered.render_html())

    async def test_forum_web_view_renders_boards_threads_and_feed(self):
        reinstall_module('forum')
        install_module('icon_fa')
        root = GDO_ForumBoard.table().get_by_aid('1')
        child = GDO_ForumBoard.create_child(root, 'Web child board')
        child_thread = GDO_ForumThread.blank({'thread_board': child.get_id(), 'thread_title': 'Child discussion'}).insert()
        for message in ('Child opening', 'Child reply'):
            GDO_ForumPost.blank({'post_thread': child_thread.get_id(), 'post_creator': cli_gizmore().get_id(),
                                 'post_message_input': message, 'post_message_editor': 'html'}).insert()
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Web root discussion'}).insert()
        GDO_ForumPost.blank({'post_thread': discussion.get_id(), 'post_creator': cli_gizmore().get_id(),
                             'post_message_input': 'Opening', 'post_message_editor': 'html'}).insert()
        previous = WebPlug.COOKIES.copy()
        try:
            WebPlug.COOKIES = {'GDO': GDO_Session.for_user(cli_gizmore()).cookie_value()}
            page = web_plug(f'forum.forum.id.{root.get_id()}.html').exec()
            self.assertIn('Web child board', page)
            self.assertIn('Web root discussion', page)
            self.assertIn('forum.rss.rss', page)
            self.assertNotIn('Traceback (most recent call last)', page)
            from bs4 import BeautifulSoup
            child_link = BeautifulSoup(page, 'html.parser').find('a', string=lambda value: value and 'Web child board' in value)
            self.assertIsNotNone(child_link)
            row = child_link.find_parent('tr')
            self.assertIsNotNone(row)
            self.assertIsNotNone(row.find('span', {'data-ts': True}))
            self.assertIn('1', [cell.get_text(strip=True) for cell in row.find_all('td')])
        finally:
            WebPlug.COOKIES = previous

    async def test_board_listing_shows_edit_button_replies_and_last_post(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        child = GDO_ForumBoard.create_child(root, 'Development')
        thread_gdo = GDO_ForumThread.blank({
            'thread_board': child.get_id(),
            'thread_title': 'Welcome',
        }).insert()
        for message in ('Opening post.', 'A reply.'):
            GDO_ForumPost.blank({
                'post_thread': thread_gdo.get_id(),
                'post_creator': cli_gizmore().get_id(),
                'post_message_input': message,
                'post_message_editor': 'html',
            }).insert()

        self.assertEqual(2, child.num_posts())
        self.assertEqual(1, child.num_replies())
        self.assertIsNotNone(child.last_post_date())

        method = boards().input('board', root.get_id())
        method.parameters()
        staff = MagicMock()
        staff.is_staff.return_value = True
        with patch.object(GDO_User, 'current', return_value=staff):
            title, replies, last_post, num_threads = method.gdo_table_headers()
        self.assertIsInstance(title, GDT_Button)
        self.assertEqual('replies', replies.get_name())
        self.assertTrue(replies.is_shrink())
        self.assertEqual('last_post_date', last_post.get_name())
        self.assertEqual('num_threads', num_threads.get_name())
        self.assertTrue(num_threads.is_shrink())
        self.assertIn(f'id.{child.get_id()}.html', method.render_board_title(title.gdo(child), child))

    def test_board_crud_only_edits_board_metadata(self):
        method = board_crud()
        fields = method.gdo_form_fields(GDO_ForumBoard.table())

        self.assertEqual(
            ['board_name', 'board_title', 'board_threads_allowed', 'board_icon', 'board_permission'],
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

    async def test_thread_crud_web_edit_saves_title_and_board(self):
        reinstall_module('forum')
        install_module('icon_fa')
        root = GDO_ForumBoard.table().get_by_aid('1')
        destination = GDO_ForumBoard.create_child(root, 'Thread destination')
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Old title'}).insert()
        previous = WebPlug.COOKIES.copy()
        from bs4 import BeautifulSoup
        try:
            WebPlug.COOKIES = {'GDO': GDO_Session.for_user(cli_gizmore()).cookie_value()}
            path = f'forum.thread_crud.id.{discussion.get_id()}.html'
            with patch.object(GDO_User, 'is_staff', return_value=True), \
                 patch.object(GDO_Permission, 'has_permission', return_value=True), \
                 patch.object(GDT_CSRF, 'validate', strict_csrf):
                page = web_plug(path).exec()
                self.assertNotIn('thread_board', BeautifulSoup(page, 'html.parser').get_text(' ', strip=True))
                token = BeautifulSoup(page, 'html.parser').find('input', {'name': 'csrf'})['value']
                response = web_plug(path).post({'thread_board': destination.get_id(), 'thread_title': 'New title',
                                               'edit': '1', 'csrf': token}).exec()
                row = GDO_ForumThread.table().select().where(
                    f'thread_id={int(discussion.get_id())}').nocache().exec().fetch_object()
                self.assertEqual('New title', row.gdo_val('thread_title'),
                                 BeautifulSoup(response, 'html.parser').get_text(' ', strip=True)[:500])
                self.assertEqual(destination.get_id(), row.gdo_val('thread_board'))
        finally:
            WebPlug.COOKIES = previous

    async def test_thread_view_shows_manage_link_only_to_staff(self):
        reinstall_module('forum')
        install_module('icon_fa')
        root = GDO_ForumBoard.table().get_by_aid('1')
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Staff controls'}).insert()
        previous = WebPlug.COOKIES.copy()
        try:
            WebPlug.COOKIES = {'GDO': GDO_Session.for_user(cli_gizmore()).cookie_value()}
            path = f'forum.thread.id.{discussion.get_id()}.html'
            with patch.object(GDO_User, 'is_staff', return_value=False):
                self.assertNotIn('forum.thread_crud.id.', web_plug(path).exec())
            with patch.object(GDO_User, 'is_staff', return_value=True):
                self.assertIn(f'forum.thread_crud.id.{discussion.get_id()}.html', web_plug(path).exec())
        finally:
            WebPlug.COOKIES = previous

    async def test_thread_view_links_to_current_board_after_move(self):
        reinstall_module('forum')
        install_module('icon_fa')
        root = GDO_ForumBoard.table().get_by_aid('1')
        destination = GDO_ForumBoard.create_child(root, 'Thread link destination')
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Moved discussion'}).insert()
        discussion.save_val('thread_board', destination.get_id())
        page = web_plug(f'forum.thread.id.{discussion.get_id()}.html').exec()
        from bs4 import BeautifulSoup
        link = next((anchor for anchor in BeautifulSoup(page, 'html.parser').find_all('a')
                     if 'Back to board' in anchor.get_text(' ', strip=True)), None)
        self.assertIsNotNone(link)
        self.assertIn(f'forum.forum.id.{destination.get_id()}.html', link.get('href'))

    async def test_empty_thread_view_shows_escaped_thread_title(self):
        reinstall_module('forum')
        install_module('icon_fa')
        root = GDO_ForumBoard.table().get_by_aid('1')
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': '<script>Empty title</script>'}).insert()
        page = web_plug(f'forum.thread.id.{discussion.get_id()}.html').exec()
        self.assertIn('&lt;script&gt;Empty title&lt;/script&gt;', page)
        self.assertNotIn('<script>Empty title</script>', page)

    async def test_thread_admin_warns_and_deletes_posts_with_thread(self):
        reinstall_module('forum')
        install_module('icon_fa')
        root = GDO_ForumBoard.table().get_by_aid('1')
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Delete discussion'}).insert()
        post = GDO_ForumPost.blank({'post_thread': discussion.get_id(), 'post_creator': cli_gizmore().get_id(),
                                    'post_message_input': 'Opening', 'post_message_editor': 'html'}).insert()
        like = GDO_ForumLikes.blank({'like_object': post.get_id(), 'like_user': cli_gizmore().get_id(), 'like_value': '1'}).insert()
        self.assertIsNotNone(like.gdo_val('like_created'))
        previous = WebPlug.COOKIES.copy()
        from bs4 import BeautifulSoup
        try:
            WebPlug.COOKIES = {'GDO': GDO_Session.for_user(cli_gizmore()).cookie_value()}
            path = f'forum.thread_crud.id.{discussion.get_id()}.html'
            with patch.object(GDO_User, 'is_staff', return_value=True), \
                 patch.object(GDO_Permission, 'has_permission', return_value=True), \
                 patch.object(GDT_CSRF, 'validate', strict_csrf):
                page = web_plug(path).exec()
                self.assertIn('Deleting this thread hides it while preserving its posts and likes.', BeautifulSoup(page, 'html.parser').get_text(' ', strip=True))
                token = BeautifulSoup(page, 'html.parser').find('input', {'name': 'csrf'})['value']
                web_plug(path).post({'thread_board': root.get_id(), 'thread_title': 'Delete discussion',
                                     'delete': '1', 'csrf': token}).exec()
                self.assertIsNotNone(GDO_ForumThread.table().get_by_aid(discussion.get_id()).gdo_val('thread_deleted'))
                self.assertIsNone(GDO_ForumThread.table().get_by_aid(discussion.get_id()).get_board())
                self.assertEqual(0, int(GDO_ForumThread.table().select('COUNT(*)').where(
                    f'thread_id={int(discussion.get_id())} AND thread_deleted IS NULL').exec().fetch_val()))
                self.assertNotIn(discussion.get_id(), GDT_Thread('thread').gdo_choices())
                self.assertNotIn('Delete discussion', web_plug(f'forum.forum.id.{root.get_id()}.html').exec())
                self.assertNotIn('Delete discussion', web_plug('forum.rss.rss').exec())
                self.assertNotIn('Opening', web_plug(f'forum.thread.id.{discussion.get_id()}.html').exec())
                self.assertIsNotNone(GDO_ForumPost.table().select('post_id').where(
                    f'post_id={int(post.get_id())}').nocache().exec().fetch_assoc())
                self.assertEqual(1, int(GDO_ForumLikes.table().select('COUNT(*)').where(
                    f'like_object={int(post.get_id())}').exec().fetch_val()))
        finally:
            WebPlug.COOKIES = previous

    async def test_failed_thread_delete_rolls_back_likes(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        user = cli_gizmore()
        Application.set_current_user(user)
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Rollback thread'}).insert()
        post = GDO_ForumPost.blank({'post_thread': discussion.get_id(), 'post_creator': user.get_id(),
                                    'post_message_input': 'Keep me', 'post_message_editor': 'html'}).insert()
        GDO_ForumLikes.blank({'like_object': post.get_id(), 'like_user': user.get_id(), 'like_value': '1'}).insert()
        method = thread_crud().env_user(user).env_server(Bash.get_server()).env_mode(Mode.render_cli)
        method.input('id', discussion.get_id()).input('thread_board', root.get_id())
        method.input('thread_title', 'Rollback thread').input('delete', '1')
        with patch.object(Application, 'IS_HTTP', False), \
             patch.object(GDO_User, 'is_staff', return_value=True), \
             patch.object(GDO_Permission, 'has_permission', return_value=True), \
             patch.object(GDO_ForumThread, 'delete', side_effect=RuntimeError('simulated delete failure')):
            Application.request_method('POST')
            with self.assertRaisesRegex(RuntimeError, 'simulated delete failure'):
                await method.execute()
        self.assertEqual(1, int(GDO_ForumLikes.table().select('COUNT(*)').where(
            f'like_object={int(post.get_id())}').exec().fetch_val()))
        self.assertIsNotNone(GDO_ForumThread.table().get_by_aid(discussion.get_id()))

    async def test_handled_gdo_error_rolls_back_thread_delete_likes(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        user = cli_gizmore()
        Application.set_current_user(user)
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Handled rollback'}).insert()
        post = GDO_ForumPost.blank({'post_thread': discussion.get_id(), 'post_creator': user.get_id(),
                                    'post_message_input': 'Keep this too', 'post_message_editor': 'html'}).insert()
        GDO_ForumLikes.blank({'like_object': post.get_id(), 'like_user': user.get_id(), 'like_value': '1'}).insert()
        method = thread_crud().env_user(user).env_server(Bash.get_server()).env_mode(Mode.render_cli)
        method.input('id', discussion.get_id()).input('thread_board', root.get_id())
        method.input('thread_title', 'Handled rollback').input('delete', '1')
        with patch.object(Application, 'IS_HTTP', False), \
             patch.object(GDO_User, 'is_staff', return_value=True), \
             patch.object(GDO_Permission, 'has_permission', return_value=True), \
             patch.object(GDO_ForumThread, 'delete', side_effect=GDOError('simulated_gdo_error')):
            Application.request_method('POST')
            await method.execute()
        self.assertEqual(1, int(GDO_ForumLikes.table().select('COUNT(*)').where(
            f'like_object={int(post.get_id())}').exec().fetch_val()))
        self.assertIsNotNone(GDO_ForumThread.table().get_by_aid(discussion.get_id()))

    async def test_nested_gdo_error_reaches_transaction_owner(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        user = cli_gizmore()
        Application.set_current_user(user)
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Nested rollback'}).insert()
        post = GDO_ForumPost.blank({'post_thread': discussion.get_id(), 'post_creator': user.get_id(),
                                    'post_message_input': 'Keep nested', 'post_message_editor': 'html'}).insert()
        GDO_ForumLikes.blank({'like_object': post.get_id(), 'like_user': user.get_id(), 'like_value': '1'}).insert()
        method = thread_crud().env_user(user).env_server(Bash.get_server()).env_mode(Mode.render_cli)
        method.input('id', discussion.get_id()).input('thread_board', root.get_id())
        method.input('thread_title', 'Nested rollback').input('delete', '1')
        db = Application.db()
        with patch.object(Application, 'IS_HTTP', False), \
             patch.object(GDO_User, 'is_staff', return_value=True), \
             patch.object(GDO_Permission, 'has_permission', return_value=True), \
             patch.object(GDO_ForumThread, 'delete', side_effect=GDOError('nested_gdo_error')):
            Application.request_method('POST')
            db.begin()
            try:
                with self.assertRaises(GDOError):
                    await method.execute()
            finally:
                db.rollback()
        self.assertEqual(1, int(GDO_ForumLikes.table().select('COUNT(*)').where(
            f'like_object={int(post.get_id())}').exec().fetch_val()))

    async def test_thread_crud_web_create_saves_title_and_board(self):
        reinstall_module('forum')
        install_module('icon_fa')
        root = GDO_ForumBoard.table().get_by_aid('1')
        previous = WebPlug.COOKIES.copy()
        from bs4 import BeautifulSoup
        try:
            WebPlug.COOKIES = {'GDO': GDO_Session.for_user(cli_gizmore()).cookie_value()}
            path = 'forum.thread_crud.html'
            with patch.object(GDO_User, 'is_staff', return_value=True), \
                 patch.object(GDO_Permission, 'has_permission', return_value=True), \
                 patch.object(GDT_CSRF, 'validate', strict_csrf):
                page = web_plug(path).exec()
                token = BeautifulSoup(page, 'html.parser').find('input', {'name': 'csrf'})['value']
                response = web_plug(path).post({'thread_board': root.get_id(), 'thread_title': 'Admin topic',
                                               'create': '1', 'csrf': token}).exec()
                discussion = GDO_ForumThread.table().get_by_vals({'thread_title': 'Admin topic'})
                self.assertIsNotNone(discussion, BeautifulSoup(response, 'html.parser').get_text(' ', strip=True)[:500])
                self.assertEqual(root.get_id(), discussion.gdo_val('thread_board'))
        finally:
            WebPlug.COOKIES = previous

    async def test_new_thread_creates_its_opening_post(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        Application.set_current_user(cli_gizmore())
        method = new_thread().input('thread_board', root.get_id()).input(
            'thread_title', 'Welcome').input(
            'post_message_input', 'This is the opening post.').input(
            'post_message_editor', 'html')
        method.parameters()

        result = method.form_submitted()

        thread_gdo = GDO_ForumThread.table().get_by_vals({'thread_title': 'Welcome'})
        post = GDO_ForumPost.table().get_by_vals({'post_thread': thread_gdo.get_id()})
        self.assertEqual(root.get_id(), thread_gdo.get_board().get_id())
        self.assertEqual(cli_gizmore().get_id(), post.gdo_val('post_creator'))
        self.assertEqual('This is the opening post.', post.gdo_val('post_message_input'))
        self.assertIn(f'forum.thread.id.{thread_gdo.get_id()}', result.get_fields()[0].render_href())
        card = post.render_card()
        self.assertIn('Welcome', card)
        self.assertIn('This is the opening post.', card)
        self.assertIn('gdo-forum-post-message', card)

    async def test_new_thread_web_form_checks_csrf_and_creates_opening_post(self):
        reinstall_module('forum')
        install_module('icon_fa')
        root = GDO_ForumBoard.table().get_by_aid('1')
        user = cli_gizmore()
        old_cookies = WebPlug.COOKIES.copy()
        try:
            WebPlug.COOKIES = {'GDO': GDO_Session.for_user(user).cookie_value()}
            path = f'forum.new_thread.thread_board.{root.get_id()}.html'
            from bs4 import BeautifulSoup
            page = web_plug(path).exec()
            token = BeautifulSoup(page, 'html.parser').find('input', {'name': 'csrf'})['value']
            fields = {'thread_board': root.get_id(), 'thread_title': 'Web creation',
                      'post_message_input': 'Opening through web', 'post_message_editor': 'html', 'create': '1'}
            with patch.object(GDT_CSRF, 'validate', strict_csrf):
                web_plug(path).post({**fields, 'csrf': 'invalid'}).exec()
            self.assertIsNone(GDO_ForumThread.table().get_by_vals({'thread_title': 'Web creation'}))
            with patch.object(GDT_CSRF, 'validate', strict_csrf):
                response = web_plug(path).post({**fields, 'csrf': token}).exec()
            discussion = GDO_ForumThread.table().get_by_vals({'thread_title': 'Web creation'})
            self.assertIsNotNone(discussion)
            post = GDO_ForumPost.table().get_by_vals({'post_thread': discussion.get_id()})
            self.assertEqual('Opening through web', post.gdo_val('post_message_input'))
            self.assertIn(f'forum.thread.id.{discussion.get_id()}', response)
        finally:
            WebPlug.COOKIES = old_cookies

    async def test_get_with_valid_csrf_never_submits_forum_forms(self):
        reinstall_module('forum')
        install_module('icon_fa')
        root = GDO_ForumBoard.table().get_by_aid('1')
        previous = WebPlug.COOKIES.copy()
        from bs4 import BeautifulSoup
        from urllib.parse import urlencode
        try:
            WebPlug.COOKIES = {'GDO': GDO_Session.for_user(cli_gizmore()).cookie_value()}
            path = f'forum.new_thread.thread_board.{root.get_id()}.html'
            with patch.object(GDT_CSRF, 'validate', strict_csrf):
                page = web_plug(path).exec()
                token = BeautifulSoup(page, 'html.parser').find('input', {'name': 'csrf'})['value']
                query = urlencode({'thread_board': root.get_id(), 'thread_title': 'GET must not create',
                                   'post_message_input': 'No mutation', 'post_message_editor': 'html',
                                   'create': '1', 'csrf': token})
                web_plug(path + '?' + query).exec()
                self.assertIsNone(GDO_ForumThread.table().get_by_vals({'thread_title': 'GET must not create'}))
        finally:
            WebPlug.COOKIES = previous

    async def test_get_cannot_reply_edit_thread_or_delete_board(self):
        reinstall_module('forum')
        install_module('icon_fa')
        root = GDO_ForumBoard.table().get_by_aid('1')
        leaf = GDO_ForumBoard.create_child(root, 'GET protected leaf')
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'GET protected thread'}).insert()
        previous = WebPlug.COOKIES.copy()
        from bs4 import BeautifulSoup
        from urllib.parse import urlencode
        try:
            WebPlug.COOKIES = {'GDO': GDO_Session.for_user(cli_gizmore()).cookie_value()}
            with patch.object(GDO_User, 'is_staff', return_value=True), \
                 patch.object(GDO_Permission, 'has_permission', return_value=True), \
                 patch.object(GDT_CSRF, 'validate', strict_csrf):
                cases = [
                    (f'forum.reply.thread.{discussion.get_id()}.html',
                     {'post_message_input': 'GET reply', 'post_message_editor': 'html', 'reply': '1'}),
                    (f'forum.thread_crud.id.{discussion.get_id()}.html',
                     {'thread_title': 'GET changed title', 'thread_board': root.get_id(), 'edit': '1'}),
                    (f'forum.board_crud.id.{leaf.get_id()}.html',
                     {'board_name': leaf.gdo_val('board_name'), 'board_title': leaf.gdo_val('board_title'),
                      'board_threads_allowed': '1', 'board_parent': root.get_id(), 'delete': '1'}),
                ]
                for path, fields in cases:
                    page = web_plug(path).exec()
                    token = BeautifulSoup(page, 'html.parser').find('input', {'name': 'csrf'})['value']
                    web_plug(path + '?' + urlencode({**fields, 'csrf': token})).exec()
                self.assertEqual(0, int(GDO_ForumPost.table().select('COUNT(*)').where(
                    f'post_thread={int(discussion.get_id())}').exec().fetch_val()))
                fresh_thread = GDO_ForumThread.table().get_by_aid(discussion.get_id())
                self.assertEqual('GET protected thread', fresh_thread.gdo_val('thread_title'))
                self.assertIsNotNone(GDO_ForumBoard.table().select('board_id').where(
                    f'board_id={int(leaf.get_id())}').nocache().exec().fetch_assoc())
                self.assertIn('GET protected thread', web_plug(f'forum.threads.board.{root.get_id()}.html').exec())
        finally:
            WebPlug.COOKIES = previous

    async def test_thread_pagination_still_uses_get(self):
        reinstall_module('forum')
        install_module('icon_fa')
        root = GDO_ForumBoard.table().get_by_aid('1')
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Paged discussion'}).insert()
        for message in ('First page marker', 'Second page marker'):
            GDO_ForumPost.blank({'post_thread': discussion.get_id(), 'post_creator': cli_gizmore().get_id(),
                                 'post_message_input': message, 'post_message_editor': 'html'}).insert()
        with patch.object(thread, 'gdo_paginate_size', return_value=1):
            response = web_plug(f'forum.thread.id.{discussion.get_id()}.html?_p=2').exec()
        self.assertIn('Second page marker', response)
        self.assertNotIn('First page marker', response)

    async def test_post_permalinks_use_id_to_break_timestamp_ties_per_thread(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Tied posts'}).insert()
        other = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Other thread'}).insert()
        posts = []
        for target, message in ((other, 'Other post'), (discussion, 'First tied'), (discussion, 'Second tied')):
            posts.append(GDO_ForumPost.blank({'post_thread': target.get_id(), 'post_creator': cli_gizmore().get_id(),
                                             'post_message_input': message, 'post_message_editor': 'html'}).insert())
        table = GDO_ForumPost.table().gdo_table_name()
        Application.db().query(f"UPDATE {table} SET post_created='2026-01-01 12:00:00' "
                               f"WHERE post_id IN ({','.join(str(int(post.get_id())) for post in posts)})").close()
        with patch.object(thread, 'gdo_paginate_size', return_value=1):
            self.assertEqual(1, posts[1].thread_page())
            self.assertEqual(2, posts[2].thread_page())
            response = web_plug(f'forum.thread.id.{discussion.get_id()}.html?_p=2').exec()
        self.assertIn('Second tied', response)
        self.assertNotIn('First tied', response)
        self.assertNotIn('Other post', response)

    async def test_open_creation_form_cannot_post_after_board_closes(self):
        reinstall_module('forum')
        install_module('icon_fa')
        root = GDO_ForumBoard.table().get_by_aid('1')
        previous = WebPlug.COOKIES.copy()
        try:
            WebPlug.COOKIES = {'GDO': GDO_Session.for_user(cli_gizmore()).cookie_value()}
            path = f'forum.new_thread.thread_board.{root.get_id()}.html'
            from bs4 import BeautifulSoup
            page = web_plug(path).exec()
            token = BeautifulSoup(page, 'html.parser').find('input', {'name': 'csrf'})['value']
            Application.db().query(f'UPDATE gdo_forumboard SET board_threads_allowed=0 WHERE board_id={int(root.get_id())}')
            with patch.object(GDT_CSRF, 'validate', strict_csrf):
                web_plug(path).post({'thread_board': root.get_id(), 'thread_title': 'Late submission',
                                     'post_message_input': 'Too late', 'post_message_editor': 'html',
                                     'create': '1', 'csrf': token}).exec()
            self.assertIsNone(GDO_ForumThread.table().get_by_vals({'thread_title': 'Late submission'}))
        finally:
            WebPlug.COOKIES = previous

    async def test_reply_creates_post_for_current_user_and_thread(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        user = cli_gizmore()
        Application.set_current_user(user)
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Replies'}).insert()
        method = reply().input('thread', discussion.get_id()).input('post_message_input', 'Hello forum!').input('post_message_editor', 'html')
        method.parameters()
        self.assertTrue(method.gdo_has_permission(user))
        method.form_submitted()
        post = GDO_ForumPost.table().get_by_vals({'post_thread': discussion.get_id()})
        self.assertEqual(user.get_id(), post.gdo_val('post_creator'))
        self.assertEqual('Hello forum!', post.gdo_val('post_message_input'))

    async def test_reply_link_points_to_new_post_page(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        user = cli_gizmore()
        Application.set_current_user(user)
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Long discussion'}).insert()
        GDO_ForumPost.blank({'post_thread': discussion.get_id(), 'post_creator': user.get_id(),
                             'post_message_input': 'Opening', 'post_message_editor': 'html'}).insert()
        method = reply().input('thread', discussion.get_id()).input('post_message_input', 'Next').input('post_message_editor', 'html')
        method.parameters()
        with patch.object(thread, 'gdo_paginate_size', return_value=1):
            result = method.form_submitted()
        href = result.get_fields()[0].render_href()
        self.assertIn('_p=2', href)
        self.assertIn(f'#forum-post-{discussion.get_last_post().get_id()}', href)

    async def test_reply_cli_executes_with_named_form_fields(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        user = cli_gizmore()
        Application.set_current_user(user)
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'CLI reply'}).insert()
        method = reply().env_user(user).env_server(Bash.get_server()).env_mode(Mode.render_cli)
        method._raw_args.clear()
        method._raw_args.add_cli_line([
            f'--thread={discussion.get_id()}', '--post_message_input=Hello from CLI', '--post_message_editor=html',
        ])
        with patch.object(Application, 'IS_HTTP', False):
            await method.execute()
        post = GDO_ForumPost.table().get_by_vals({'post_thread': discussion.get_id()})
        self.assertIsNotNone(post)
        self.assertEqual('Hello from CLI', post.gdo_val('post_message_input'))

    async def test_reply_command_through_chat_parser(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Parsed reply'}).insert()
        with patch.object(Application, 'IS_HTTP', False):
            text_plug(Mode.render_cli, f'$forum.reply --thread={discussion.get_id()} '
                      '--post_message_input="Hello from chat" --post_message_editor=html', cli_gizmore())
        post = GDO_ForumPost.table().get_by_vals({'post_thread': discussion.get_id()})
        self.assertIsNotNone(post)
        self.assertEqual('Hello from chat', post.gdo_val('post_message_input'))

    async def test_reply_requires_authentication_and_board_permission(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Restricted replies'}).insert()
        method = reply().input('thread', discussion.get_id())
        method.parameters()
        guest = MagicMock()
        guest.is_authenticated.return_value = False
        self.assertFalse(method.gdo_has_permission(guest))
        user = cli_gizmore()
        with patch.object(GDO_ForumBoard, 'has_permission', return_value=False):
            self.assertFalse(method.gdo_has_permission(user))

    async def test_web_edit_forms_include_csrf(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Forms'}).insert()
        with patch.object(Application, 'IS_HTTP', True), patch.object(Application, 'current_href', return_value='/'):
            methods = [new_thread().input('thread_board', root.get_id()),
                       reply().input('thread', discussion.get_id()), board_crud(), thread_crud()]
            for method in methods:
                self.assertIsNotNone(method.get_form().get_field('csrf'), method.__class__.__name__)

    def test_staff_methods_recheck_role_even_with_cached_method_permission(self):
        user = MagicMock()
        user.is_staff.return_value = False
        for cls in (board_crud, thread_crud):
            previous = WithPermissionCheck.CACHE.get(cls)
            try:
                WithPermissionCheck.CACHE[cls] = {user: True}
                self.assertFalse(cls().has_permission(user, False))
            finally:
                if previous is None:
                    WithPermissionCheck.CACHE.pop(cls, None)
                else:
                    WithPermissionCheck.CACHE[cls] = previous

    async def test_staff_methods_reject_after_actual_role_revocation(self):
        reinstall_module('forum')
        user = cli_gizmore()
        permission = GDO_Permission.get_by_name('staff')
        was_staff = GDO_UserPermission.has_permission(user, permission)
        try:
            await GDO_UserPermission.grant_permission(user, permission)
            self.assertTrue(user.is_staff())
            for cls in (board_crud, thread_crud):
                WithPermissionCheck.CACHE.setdefault(cls, {})[user] = True
            await GDO_UserPermission.revoke_permission(user, permission)
            self.assertFalse(user.is_staff())
            for cls in (board_crud, thread_crud):
                self.assertFalse(cls().has_permission(user, False))
        finally:
            if was_staff:
                await GDO_UserPermission.grant_permission(user, permission)
            for cls in (board_crud, thread_crud):
                WithPermissionCheck.CACHE.get(cls, {}).pop(user, None)

    async def test_reply_route_shows_form_for_authenticated_user(self):
        reinstall_module('forum')
        install_module('icon_fa')
        root = GDO_ForumBoard.table().get_by_aid('1')
        user = cli_gizmore()
        Application.set_current_user(user)
        discussion = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Web replies'}).insert()
        old_cookies = WebPlug.COOKIES.copy()
        try:
            WebPlug.COOKIES = {'GDO': GDO_Session.for_user(user).cookie_value()}
            thread_page = web_plug(f'forum.thread.id.{discussion.get_id()}.html').exec()
            self.assertIn('forum.reply', thread_page)
            self.assertIn('<title>Thread</title>', thread_page)
            page = web_plug(f'forum.reply.thread.{discussion.get_id()}.html').exec()
            self.assertIn('post_message_input', page)
            self.assertIn('Reply', page)
            from bs4 import BeautifulSoup
            token = BeautifulSoup(page, 'html.parser').find('input', {'name': 'csrf'})['value']
            self.assertTrue(token)
            with patch.object(GDT_CSRF, 'validate', strict_csrf):
                web_plug(f'forum.reply.thread.{discussion.get_id()}.html').post({
                    'post_message_input': 'Untrusted reply',
                    'post_message_editor': 'html', 'reply': '1', 'csrf': 'invalid',
                }).exec()
            self.assertIsNone(GDO_ForumPost.table().get_by_vals({'post_thread': discussion.get_id()}))
            with patch.object(GDT_CSRF, 'validate', strict_csrf):
                result = web_plug(f'forum.reply.thread.{discussion.get_id()}.html').post({
                    'post_message_input': 'A reply through the web form.',
                    'post_message_editor': 'html', 'reply': '1', 'csrf': token,
                }).exec()
            self.assertIn('Your reply has been posted.', result)
            self.assertIn(f'forum.thread.id.{discussion.get_id()}', result)
            post = GDO_ForumPost.table().get_by_vals({'post_thread': discussion.get_id()})
            self.assertEqual('A reply through the web form.', post.gdo_val('post_message_input'))
            thread_page = web_plug(f'forum.thread.id.{discussion.get_id()}.html').exec()
            self.assertIn('A reply through the web form.', BeautifulSoup(thread_page, 'html.parser').get_text(' ', strip=True))
        finally:
            WebPlug.COOKIES = old_cookies

    async def test_add_thread_accepts_a_board_name_and_message_remainder(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        Application.set_current_user(cli_gizmore())
        method = add_thread().input('board', 'forum').input('title', 'Welcome').input(
            'message', 'This is the opening post.')
        method.parameters()

        await method.gdo_execute()

        thread_gdo = GDO_ForumThread.table().get_by_vals({'thread_title': 'Welcome'})
        post = GDO_ForumPost.table().get_by_vals({'post_thread': thread_gdo.get_id()})
        self.assertEqual(root.get_id(), thread_gdo.get_board().get_id())
        self.assertEqual('This is the opening post.', post.gdo_val('post_message_input'))

    async def test_thread_creation_rejects_closed_or_inaccessible_boards(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        user = cli_gizmore()
        Application.set_current_user(user)
        form = new_thread().input('thread_board', root.get_id()).input('thread_title', 'Forbidden form')
        command = add_thread().input('board', root.get_id()).input('title', 'Forbidden command').input('message', 'No')
        form.parameters()
        command.parameters()
        for condition in ('is_thread_allowed', 'has_permission'):
            with patch.object(GDO_ForumBoard, condition, return_value=False):
                self.assertFalse(form.gdo_has_permission(user))
                self.assertFalse(command.gdo_has_permission(user))
                with patch.object(form, 'err'), patch.object(command, 'err'):
                    form.form_submitted()
                    await command.gdo_execute()
        self.assertIsNone(GDO_ForumThread.table().get_by_vals({'thread_title': 'Forbidden form'}))
        self.assertIsNone(GDO_ForumThread.table().get_by_vals({'thread_title': 'Forbidden command'}))
        self.assertEqual('staff', thread_crud().gdo_user_permission())

    async def test_chat_thread_command_cannot_be_called_as_web_endpoint(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        user = cli_gizmore()
        previous = WebPlug.COOKIES.copy()
        try:
            WebPlug.COOKIES = {'GDO': GDO_Session.for_user(user).cookie_value()}
            web_plug(f'forum.add_thread.html?board={root.get_id()}&title=WebBypass&message=Hello').exec()
            web_plug('forum.add_thread.html').post({'board': root.get_id(), 'title': 'WebBypass', 'message': 'Hello'}).exec()
            self.assertIsNone(GDO_ForumThread.table().get_by_vals({'thread_title': 'WebBypass'}))
        finally:
            WebPlug.COOKIES = previous

    async def test_add_thread_cli_uses_title_then_the_message_remainder(self):
        reinstall_module('forum')
        method = add_thread()
        method._raw_args.clear()
        method._raw_args.add_cli_line([
            '--board=forum', 'Welcome', 'This', 'is', 'the', 'opening', 'post.',
        ])
        params = method.parameters()

        self.assertEqual('forum', params['board'].get_val())
        self.assertEqual('Welcome', params['title'].get_val())
        self.assertEqual('This is the opening post.', params['message'].get_value())

    async def test_add_thread_command_through_chat_parser(self):
        reinstall_module('forum')
        with patch.object(Application, 'IS_HTTP', False):
            text_plug(Mode.render_cli, '$forum.add_thread --board=forum "Chat topic" Hello from chat', cli_gizmore())
        discussion = GDO_ForumThread.table().get_by_vals({'thread_title': 'Chat topic'})
        self.assertIsNotNone(discussion)
        post = GDO_ForumPost.table().get_by_vals({'post_thread': discussion.get_id()})
        self.assertIsNotNone(post)
        self.assertEqual('Hello from chat', post.gdo_val('post_message_input'))

    async def test_add_thread_rolls_back_when_opening_post_fails(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        user = cli_gizmore()
        Application.set_current_user(user)
        method = add_thread().env_user(user).env_server(Bash.get_server()).env_mode(Mode.render_cli)
        method.input('board', root.get_id()).input('title', 'Failed opening').input('message', 'This fails')
        with patch.object(Application, 'IS_HTTP', False), \
             patch.object(GDO_ForumPost, 'insert', side_effect=GDOError('simulated_post_failure')):
            Application.request_method('POST')
            await method.execute()
        self.assertIsNone(GDO_ForumThread.table().select().where(
            "thread_title='Failed opening'").nocache().exec().fetch_object())

    async def test_new_thread_rolls_back_when_opening_post_fails(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        user = cli_gizmore()
        Application.set_current_user(user)
        method = new_thread().env_user(user).env_server(Bash.get_server()).env_mode(Mode.render_cli)
        method.input('thread_board', root.get_id()).input('thread_title', 'Failed form opening')
        method.input('post_message_input', 'This fails').input('post_message_editor', 'html')
        with patch.object(Application, 'IS_HTTP', False), \
             patch.object(GDO_ForumPost, 'insert', side_effect=GDOError('simulated_post_failure')):
            Application.request_method('POST')
            await method.execute()
        self.assertIsNone(GDO_ForumThread.table().select().where(
            "thread_title='Failed form opening'").nocache().exec().fetch_object())

    async def test_board_selector_accepts_id_or_machine_name(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        selector = GDT_ForumBoard('board')
        self.assertEqual(root.get_id(), selector.to_value(root.get_id()).get_id())
        self.assertEqual(root.get_id(), selector.to_value('forum').get_id())

    async def test_thread_selector_hides_private_choices_and_name_candidates(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        private = GDO_ForumBoard.create_child(root, 'Private thread board')
        visible = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Shared public'}).insert()
        hidden = GDO_ForumThread.blank({'thread_board': private.get_id(), 'thread_title': 'Shared private'}).insert()
        with patch.object(GDO_ForumBoard, 'has_permission', lambda board, user: board.get_id() == root.get_id()):
            selector = GDT_Thread('thread')
            self.assertNotIn(hidden.get_id(), selector.gdo_choices())
            self.assertEqual(visible.get_id(), selector.to_value('Shared').get_id())

    async def test_thread_selector_refreshes_choices_after_access_changes(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        private = GDO_ForumBoard.create_child(root, 'Revocable thread board')
        discussion = GDO_ForumThread.blank({'thread_board': private.get_id(), 'thread_title': 'Revocable topic'}).insert()
        selector = GDT_Thread('thread')
        with patch.object(GDO_ForumBoard, 'has_permission', return_value=True):
            self.assertIn(discussion.get_id(), selector.init_choices())
        with patch.object(GDO_ForumBoard, 'has_permission', return_value=False):
            self.assertNotIn(discussion.get_id(), selector.init_choices())

    async def test_thread_name_search_web_does_not_disclose_private_candidates(self):
        reinstall_module('forum')
        install_module('icon_fa')
        root = GDO_ForumBoard.table().get_by_aid('1')
        private = GDO_ForumBoard.create_child(root, 'Hidden selection board')
        visible = GDO_ForumThread.blank({'thread_board': root.get_id(), 'thread_title': 'Unique shared public'}).insert()
        GDO_ForumThread.blank({'thread_board': private.get_id(), 'thread_title': 'Unique shared secret'}).insert()
        GDO_ForumPost.blank({'post_thread': visible.get_id(), 'post_creator': cli_gizmore().get_id(),
                             'post_message_input': 'Visible discussion body', 'post_message_editor': 'html'}).insert()
        with patch.object(GDO_ForumBoard, 'has_permission', lambda board, user: board.get_id() == root.get_id()):
            page = web_plug('forum.thread.html?id=Unique+shared').exec()
            self.assertIn('Visible discussion body', page)
            self.assertNotIn('Unique shared secret', page)
            self.assertNotIn('Traceback (most recent call last)', page)

    async def test_public_board_threads_route_uses_board_name_and_ascending_date(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        method = board()
        method.env_user(cli_gizmore()).env_server(Bash.get_server()).env_session(None)
        method._raw_args.clear()
        method._raw_args.add_cli_line(['forum'])
        method.parameters()

        self.assertEqual(root.get_id(), method.param_value('board').get_id())
        self.assertEqual('/forum.board.forum.html?_lang=en', method.href(positional=('forum',)))
        rendered = await method.gdo_execute()
        listing = rendered.get_fields()[1]._table_method
        self.assertIn('MIN(post_created)', listing.gdo_table_query().build_query())

    async def test_install_creates_one_root_board(self):
        reinstall_module('forum')

        root = GDO_ForumBoard.table().get_by_aid('1')
        self.assertEqual('Forum', root.gdo_val('board_title'))
        self.assertEqual('forum', root.gdo_val('board_name'))
        self.assertEqual((1, 2), root.column('board_tree').get_value())
        self.assertEqual(1, int(GDO_ForumBoard.table().select('COUNT(*)').exec().fetch_val()))
        self.assertEqual(0, root.num_posts())

    def test_forum_main_method_is_the_root_board(self):
        self.assertEqual('forum', module_forum().gdo_main_method_name())

    async def test_install_seed_is_idempotent_and_preserves_forum_content(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        root.save_val('board_title', 'My existing forum')
        child = GDO_ForumBoard.create_child(root, 'Existing board')
        discussion = GDO_ForumThread.blank({'thread_board': child.get_id(), 'thread_title': 'Existing thread'}).insert()
        await ForumInstall.on_install()
        await ForumInstall.on_install()
        fresh_root = GDO_ForumBoard.table().select().where('board_id=1').nocache().exec().fetch_object()
        self.assertEqual('My existing forum', fresh_root.gdo_val('board_title'))
        self.assertEqual((1, 4), fresh_root.column('board_tree').get_value())
        self.assertEqual(2, int(GDO_ForumBoard.table().select('COUNT(*)').exec().fetch_val()))
        self.assertIsNotNone(GDO_ForumThread.table().get_by_aid(discussion.get_id()))

    async def test_board_name_stays_valid_when_editing_the_same_board(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')

        self.assertTrue(root.column('board_name').validate(root.gdo_val('board_name')))

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

    async def test_sidebar_hides_inaccessible_root(self):
        reinstall_module('forum')
        page = MagicMock()
        module = module_forum()
        with patch.object(GDO_ForumBoard, 'has_permission', return_value=False):
            module.gdo_init_sidebar(page)
            page._left_bar.add_field.assert_not_called()
        with patch.object(GDO_ForumBoard, 'has_permission', return_value=True):
            module.gdo_init_sidebar(page)
            page._left_bar.add_field.assert_called_once()
            link = page._left_bar.add_field.call_args.args[0]
            self.assertIn('forum.forum.id.1.html', link._href)

    async def test_parent_selector_rejects_descendant_names_and_stale_bounds(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        parent = GDO_ForumBoard.create_child(root, 'Selector parent')
        child = GDO_ForumBoard.create_child(parent, 'Selector child')
        parent.column('board_tree').set((2, 3))  # Stale cached bounds.
        selector = GDT_ForumBoard('board_parent').for_child(parent)
        self.assertIsNone(selector.to_value(child.get_id()))
        self.assertIsNone(selector.to_value(child.gdo_val('board_name')))
        self.assertIsNone(selector.to_value(parent.gdo_val('board_name')))
        self.assertEqual(root.get_id(), selector.to_value(root.gdo_val('board_name')).get_id())

    async def test_root_board_parent_selector_is_not_writable(self):
        reinstall_module('forum')
        method = board_crud().input('id', '1')
        method.parameters()
        form = GDT_Form()
        method.gdo_create_form(form)

        self.assertFalse(form.get_field('board_parent').is_writable())

    async def test_board_crud_has_labeled_create_edit_delete_actions(self):
        reinstall_module('forum')

        create_form = board_crud().get_form()
        self.assertEqual(['create'], [action.get_name() for action in create_form.actions().get_fields()])
        self.assertEqual(['Create'], [action.render_text() for action in create_form.actions().get_fields()])

        edit_method = board_crud().input('id', '1')
        edit_method.parameters()
        edit_form = edit_method.get_form()
        self.assertEqual(['edit', 'delete'], [action.get_name() for action in edit_form.actions().get_fields()])
        self.assertEqual(['Edit', 'Delete'], [action.render_text() for action in edit_form.actions().get_fields()])

    async def test_staff_forms_do_not_offer_creation_for_invalid_edit_ids(self):
        reinstall_module('forum')
        install_module('icon_fa')
        previous = WebPlug.COOKIES.copy()
        from bs4 import BeautifulSoup
        try:
            WebPlug.COOKIES = {'GDO': GDO_Session.for_user(cli_gizmore()).cookie_value()}
            with patch.object(GDO_User, 'is_staff', return_value=True), \
                 patch.object(GDO_Permission, 'has_permission', return_value=True):
                for path in ('forum.board_crud.id.999999.html', 'forum.thread_crud.id.999999.html'):
                    with self.subTest(path=path):
                        page = web_plug(path).exec()
                        self.assertIsNone(BeautifulSoup(page, 'html.parser').find('input', {'name': 'create'}))
                        self.assertNotIn('<title>Server Error</title>', page[:1000])
        finally:
            WebPlug.COOKIES = previous

    async def test_invalid_staff_edit_ids_cannot_create_via_post(self):
        reinstall_module('forum')
        install_module('icon_fa')
        root = GDO_ForumBoard.table().get_by_aid('1')
        previous = WebPlug.COOKIES.copy()
        from bs4 import BeautifulSoup
        try:
            WebPlug.COOKIES = {'GDO': GDO_Session.for_user(cli_gizmore()).cookie_value()}
            with patch.object(GDO_User, 'is_staff', return_value=True), \
                 patch.object(GDO_Permission, 'has_permission', return_value=True), \
                 patch.object(GDT_CSRF, 'validate', strict_csrf):
                for module_method, fields in (
                    ('board_crud', {'board_name': 'invalid-id-create', 'board_title': 'Invalid ID board',
                                    'board_parent': root.get_id(), 'board_threads_allowed': '1',
                                    'board_icon': '', 'board_permission': ''}),
                    ('thread_crud', {'thread_title': 'Invalid ID thread', 'thread_board': root.get_id()}),
                ):
                    page = web_plug(f'forum.{module_method}.html').exec()
                    token = BeautifulSoup(page, 'html.parser').find('input', {'name': 'csrf'})['value']
                    web_plug(f'forum.{module_method}.id.999999.html').post(
                        {**fields, 'create': '1', 'csrf': token}).exec()
            self.assertIsNone(GDO_ForumBoard.table().get_by_vals({'board_name': 'invalid-id-create'}))
            self.assertIsNone(GDO_ForumThread.table().get_by_vals({'thread_title': 'Invalid ID thread'}))
        finally:
            WebPlug.COOKIES = previous

    async def test_board_crud_saves_thread_setting_on_create_and_edit(self):
        reinstall_module('forum')
        install_module('icon_fa')
        root = GDO_ForumBoard.table().get_by_aid('1')
        previous = WebPlug.COOKIES.copy()
        from bs4 import BeautifulSoup
        try:
            WebPlug.COOKIES = {'GDO': GDO_Session.for_user(cli_gizmore()).cookie_value()}
            with patch.object(GDO_User, 'is_staff', return_value=True), \
                 patch.object(GDO_Permission, 'has_permission', return_value=True), \
                 patch.object(GDT_CSRF, 'validate', strict_csrf):
                path = 'forum.board_crud.html'
                page = web_plug(path).exec()
                token = BeautifulSoup(page, 'html.parser').find('input', {'name': 'csrf'})['value']
                fields = {'board_name': 'closed-board', 'board_title': 'Closed board',
                          'board_parent': root.get_id(), 'board_threads_allowed': '0',
                          'board_icon': '', 'board_permission': '', 'create': '1', 'csrf': token}
                created_page = web_plug(path).post(fields).exec()
                self.assertIn("Board 'Closed board' created.", BeautifulSoup(created_page, 'html.parser').get_text(' ', strip=True))
                created = GDO_ForumBoard.table().get_by_vals({'board_name': 'closed-board'})
                self.assertIsNotNone(created)
                self.assertFalse(created.is_thread_allowed())
                edit_path = f'forum.board_crud.id.{created.get_id()}.html'
                page = web_plug(edit_path).exec()
                token = BeautifulSoup(page, 'html.parser').find('input', {'name': 'csrf'})['value']
                edit_fields = {key: value for key, value in fields.items() if key != 'create'}
                response = web_plug(edit_path).post({**edit_fields, 'board_threads_allowed': '1',
                                                     'edit': '1', 'csrf': token}).exec()
                self.assertIn("Board 'Closed board' updated.", BeautifulSoup(response, 'html.parser').get_text(' ', strip=True))
                self.assertTrue(created.is_thread_allowed(), BeautifulSoup(response, 'html.parser').get_text(' ', strip=True)[:1000])
        finally:
            WebPlug.COOKIES = previous

    async def test_board_crud_web_move_updates_tree_and_title(self):
        reinstall_module('forum')
        install_module('icon_fa')
        root = GDO_ForumBoard.table().get_by_aid('1')
        source = GDO_ForumBoard.create_child(root, 'Web move source')
        destination = GDO_ForumBoard.create_child(root, 'Web move destination')
        previous = WebPlug.COOKIES.copy()
        from bs4 import BeautifulSoup
        try:
            WebPlug.COOKIES = {'GDO': GDO_Session.for_user(cli_gizmore()).cookie_value()}
            path = f'forum.board_crud.id.{source.get_id()}.html'
            with patch.object(GDO_User, 'is_staff', return_value=True), \
                 patch.object(GDO_Permission, 'has_permission', return_value=True), \
                 patch.object(GDT_CSRF, 'validate', strict_csrf):
                page = web_plug(path).exec()
                token = BeautifulSoup(page, 'html.parser').find('input', {'name': 'csrf'})['value']
                response = web_plug(path).post({
                    'board_name': source.gdo_val('board_name'), 'board_title': 'Moved board',
                    'board_threads_allowed': '1', 'board_icon': '', 'board_permission': '',
                    'board_parent': destination.get_id(), 'edit': '1', 'csrf': token,
                }).exec()
                fresh = GDO_ForumBoard.table().select().where(
                    f'board_id={int(source.get_id())}').nocache().exec().fetch_object()
                self.assertEqual('Moved board', fresh.gdo_val('board_title'),
                                 BeautifulSoup(response, 'html.parser').get_text(' ', strip=True)[:500])
                self.assertEqual(destination.get_id(), fresh.parent().get_id())
        finally:
            WebPlug.COOKIES = previous

    async def test_board_crud_web_rejects_move_to_descendant(self):
        reinstall_module('forum')
        install_module('icon_fa')
        root = GDO_ForumBoard.table().get_by_aid('1')
        source = GDO_ForumBoard.create_child(root, 'Cycle source')
        child = GDO_ForumBoard.create_child(source, 'Cycle child')
        previous = WebPlug.COOKIES.copy()
        from bs4 import BeautifulSoup
        try:
            WebPlug.COOKIES = {'GDO': GDO_Session.for_user(cli_gizmore()).cookie_value()}
            path = f'forum.board_crud.id.{source.get_id()}.html'
            with patch.object(GDO_User, 'is_staff', return_value=True), \
                 patch.object(GDO_Permission, 'has_permission', return_value=True), \
                 patch.object(GDT_CSRF, 'validate', strict_csrf):
                page = web_plug(path).exec()
                token = BeautifulSoup(page, 'html.parser').find('input', {'name': 'csrf'})['value']
                web_plug(path).post({
                    'board_name': source.gdo_val('board_name'), 'board_title': 'Must not save',
                    'board_threads_allowed': '1', 'board_icon': '', 'board_permission': '',
                    'board_parent': child.gdo_val('board_name'), 'edit': '1', 'csrf': token,
                }).exec()
                fresh = GDO_ForumBoard.table().select().where(
                    f'board_id={int(source.get_id())}').nocache().exec().fetch_object()
                self.assertEqual('Cycle source', fresh.gdo_val('board_title'))
                self.assertEqual(root.get_id(), fresh.parent().get_id())
        finally:
            WebPlug.COOKIES = previous

    async def test_board_deletion_rejects_root_children_and_threads(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        parent = GDO_ForumBoard.create_child(root, 'Delete parent')
        child = GDO_ForumBoard.create_child(parent, 'Delete child')
        GDO_ForumThread.blank({'thread_board': child.get_id(), 'thread_title': 'Protected thread'}).insert()
        for board_gdo in (root, parent, child):
            method = board_crud().input('id', board_gdo.get_id())
            method.parameters()
            with patch.object(method, 'err') as err, patch.object(method, 'get_form', return_value=MagicMock()):
                method.on_delete()
                err.assert_called_once_with('err_forum_board_not_empty')
            self.assertIsNotNone(GDO_ForumBoard.table().get_by_aid(board_gdo.get_id()))

    async def test_board_deletion_web_protects_nonempty_and_deletes_empty(self):
        reinstall_module('forum')
        install_module('icon_fa')
        root = GDO_ForumBoard.table().get_by_aid('1')
        empty = GDO_ForumBoard.create_child(root, 'Web empty')
        occupied = GDO_ForumBoard.create_child(root, 'Web occupied')
        GDO_ForumThread.blank({'thread_board': occupied.get_id(), 'thread_title': 'Keep me'}).insert()
        previous = WebPlug.COOKIES.copy()
        from bs4 import BeautifulSoup
        try:
            WebPlug.COOKIES = {'GDO': GDO_Session.for_user(cli_gizmore()).cookie_value()}
            with patch.object(GDO_User, 'is_staff', return_value=True), \
                 patch.object(GDO_Permission, 'has_permission', return_value=True), \
                 patch.object(GDT_CSRF, 'validate', strict_csrf):
                for target, should_exist in ((occupied, True), (empty, False)):
                    path = f'forum.board_crud.id.{target.get_id()}.html'
                    page = web_plug(path).exec()
                    token = BeautifulSoup(page, 'html.parser').find('input', {'name': 'csrf'})['value']
                    web_plug(path).post({
                        'board_name': target.gdo_val('board_name'), 'board_title': target.gdo_val('board_title'),
                        'board_threads_allowed': '1', 'board_icon': '', 'board_permission': '',
                        'board_parent': root.get_id(), 'delete': '1', 'csrf': token,
                    }).exec()
                    exists = GDO_ForumBoard.table().select('board_id').where(
                        f'board_id={int(target.get_id())}').nocache().exec().fetch_assoc()
                    self.assertEqual(should_exist, bool(exists))
        finally:
            WebPlug.COOKIES = previous

    async def test_board_deletion_allows_an_empty_leaf(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        leaf = GDO_ForumBoard.create_child(root, 'Empty leaf')
        leaf_id = leaf.get_id()
        method = board_crud().input('id', leaf_id)
        method.parameters()
        with patch.object(method, 'msg'), patch.object(method, 'get_form', return_value=MagicMock()):
            method.on_delete()
        self.assertIsNone(GDO_ForumBoard.table().select().where(f'board_id={int(leaf_id)}').nocache().exec().fetch_object())
        with self.assertRaisesRegex(ValueError, 'parent board no longer exists'):
            GDO_ForumBoard.create_child(leaf, 'Orphan')
        replacement = GDO_ForumBoard.create_child(root, 'Replacement leaf')
        self.assertEqual(root.get_id(), replacement.parent().get_id())

    async def test_tree_lock_excludes_a_second_transaction(self):
        reinstall_module('forum')
        db = Application.db()
        other = Database(db.db_host, db.db_name, db.username, db.password)
        link = db.get_link()
        other_link = other.get_link()
        other.query('SET SESSION innodb_lock_wait_timeout=1').close()
        table = GDO_ForumBoard.table().gdo_table_name()
        try:
            link.start_transaction()
            GDO_ForumBoard.lock_tree()
            other_link.start_transaction()
            with self.assertRaises(GDODBException):
                other.select(f'SELECT board_id FROM {table} ORDER BY board_id FOR UPDATE', False)
            other_link.rollback()
            link.rollback()
            other_link.start_transaction()
            result = other.select(f'SELECT board_id FROM {table} ORDER BY board_id FOR UPDATE', False)
            self.assertIsNotNone(result.fetch_row())
            result.close()
        finally:
            if link.in_transaction:
                link.rollback()
            if other_link.in_transaction:
                other_link.rollback()
            other_link.close()
            other.link = None

    async def test_thread_cannot_move_into_board_being_deleted(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        leaf = GDO_ForumBoard.create_child(root, 'Deletion race target')
        discussion = GDO_ForumThread.blank({
            'thread_board': root.get_id(), 'thread_title': 'Concurrent move',
        }).insert()
        db = Application.db()
        other = Database(db.db_host, db.db_name, db.username, db.password)
        link = db.get_link()
        other_link = other.get_link()
        other.query('SET SESSION innodb_lock_wait_timeout=1').close()
        threads = GDO_ForumThread.table().gdo_table_name()
        move = (f'UPDATE {threads} SET thread_board={int(leaf.get_id())} '
                f'WHERE thread_id={int(discussion.get_id())}')
        try:
            link.start_transaction()
            GDO_ForumBoard.lock_tree()
            other_link.start_transaction()
            with self.assertRaises(GDODBException):
                other.select(move, False)
            other_link.rollback()
            method = board_crud().input('id', leaf.get_id())
            method.parameters()
            with patch.object(method, 'msg'), patch.object(method, 'get_form', return_value=MagicMock()):
                method.on_delete()
            link.commit()
            other_link.start_transaction()
            with self.assertRaises(GDODBException):
                other.select(move, False)
            other_link.rollback()
            row = GDO_ForumThread.table().select('thread_board').where(
                f'thread_id={int(discussion.get_id())}').nocache().exec().fetch_assoc()
            self.assertEqual(root.get_id(), str(row['thread_board']))
        finally:
            if link.in_transaction:
                link.rollback()
            if other_link.in_transaction:
                other_link.rollback()
            other_link.close()
            other.link = None

    async def test_board_deletion_sees_a_new_thread_despite_old_snapshot(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        leaf = GDO_ForumBoard.create_child(root, 'Snapshot race target')
        discussion = GDO_ForumThread.blank({
            'thread_board': root.get_id(), 'thread_title': 'Concurrent arrival',
        }).insert()
        db = Application.db()
        other = Database(db.db_host, db.db_name, db.username, db.password)
        link = db.get_link()
        other_link = other.get_link()
        threads = GDO_ForumThread.table().gdo_table_name()
        try:
            link.start_transaction()
            db.select(f'SELECT thread_id FROM {threads} WHERE thread_board={int(leaf.get_id())}', False).fetch_row()
            other.query(f'UPDATE {threads} SET thread_board={int(leaf.get_id())} '
                        f'WHERE thread_id={int(discussion.get_id())}').close()
            method = board_crud().input('id', leaf.get_id())
            method.parameters()
            with patch.object(method, 'err') as err, patch.object(method, 'get_form', return_value=MagicMock()):
                method.on_delete()
                err.assert_called_once_with('err_forum_board_not_empty')
            link.rollback()
            self.assertIsNotNone(GDO_ForumBoard.table().select().where(
                f'board_id={int(leaf.get_id())}').nocache().exec().fetch_object())
        finally:
            if link.in_transaction:
                link.rollback()
            other_link.close()
            other.link = None

    async def test_child_board_can_move_to_another_parent(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        alpha = GDO_ForumBoard.create_child(root, 'Alpha')
        beta = GDO_ForumBoard.create_child(root, 'Beta')

        alpha.move_to(beta)

        self.assertEqual((1, 6), root.column('board_tree').get_value())
        self.assertEqual((2, 5), beta.column('board_tree').get_value())
        self.assertEqual((3, 4), alpha.column('board_tree').get_value())

    async def test_parent_lookup_uses_database_after_tree_rollback(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        alpha = GDO_ForumBoard.create_child(root, 'Rollback parent alpha')
        beta = GDO_ForumBoard.create_child(root, 'Rollback parent beta')
        db = Application.db()
        db.begin()
        try:
            alpha.move_to(beta)
            self.assertEqual(beta.get_id(), alpha.parent().get_id())
        finally:
            db.rollback()
        self.assertEqual(root.get_id(), alpha.parent().get_id())

    async def test_rolled_back_board_insert_is_not_retrieved_from_cache(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        db = Application.db()
        db.begin()
        try:
            transient = GDO_ForumBoard.create_child(root, 'Transient board')
            transient_id = transient.get_id()
        finally:
            db.rollback()
        self.assertIsNone(GDO_ForumBoard.table().get_by_aid(transient_id))
        fresh_root = GDO_ForumBoard.table().get_by_aid(root.get_id())
        self.assertEqual((1, 2), fresh_root.column('board_tree').get_value())

    async def test_nested_rollback_evicts_updated_and_deleted_boards(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        child = GDO_ForumBoard.create_child(root, 'Nested cache child')
        child_id = child.get_id()
        db = Application.db()
        db.begin()
        try:
            root.save_val('board_title', 'Uncommitted title')
            db.begin()
            child.delete()
            db.commit()  # The outer transaction is still open.
        finally:
            db.rollback()
        fresh_root = GDO_ForumBoard.table().get_by_aid(root.get_id())
        fresh_child = GDO_ForumBoard.table().get_by_aid(child_id)
        self.assertEqual('Forum', fresh_root.gdo_val('board_title'))
        self.assertIsNotNone(fresh_child)
        self.assertEqual('Nested cache child', fresh_child.gdo_val('board_title'))

    async def test_committed_board_remains_available_after_transaction(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        db = Application.db()
        db.begin()
        try:
            child = GDO_ForumBoard.create_child(root, 'Committed board')
            child_id = child.get_id()
            db.commit()
        except Exception:
            db.rollback()
            raise
        self.assertEqual('Committed board', GDO_ForumBoard.table().get_by_aid(child_id).gdo_val('board_title'))

    async def test_board_crud_move_uses_current_tree_not_cached_parent(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        alpha = GDO_ForumBoard.create_child(root, 'Move alpha')
        beta = GDO_ForumBoard.create_child(root, 'Move beta')
        alpha.move_to(beta)
        method = board_crud()
        with patch.object(method, 'crud_gdo', return_value=alpha), \
             patch.object(method, 'param_value', return_value=root), \
             patch.object(alpha, 'parent', return_value=root), \
             patch.object(MethodCrud, 'on_update', return_value=None):
            method.on_update()
        self.assertEqual(root.get_id(), alpha.parent().get_id())

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

    async def test_board_children_ignore_stale_cached_tree_bounds(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        alpha = GDO_ForumBoard.create_child(root, 'Stale parent')
        child = GDO_ForumBoard.create_child(alpha, 'Current child')
        method = boards().input('board', alpha.get_id())
        method.parameters()
        alpha.column('board_tree').set((2, 3))
        result = method.gdo_table_query().exec().fetch_all()
        self.assertEqual([child.get_id()], [entry.get_id() for entry in result])

    async def test_boards_exposes_actions_for_the_current_board(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        method = boards().input('board', root.get_id())
        method.parameters()

        staff = MagicMock()
        staff.is_staff.return_value = True
        staff.is_authenticated.return_value = True
        with patch.object(GDO_User, 'current', return_value=staff):
            actions = method.board_actions().get_fields()

        self.assertEqual(['new_board', 'edit_board', 'new_thread'], [action.get_name() for action in actions])
        self.assertIn(f'board_parent.{root.get_id()}', actions[0].render_href())
        self.assertIn(f'id.{root.get_id()}', actions[1].render_href())
        self.assertIn(f'forum.new_thread.thread_board.{root.get_id()}', actions[2].render_href())

    async def test_board_actions_match_viewer_permissions(self):
        reinstall_module('forum')
        root = GDO_ForumBoard.table().get_by_aid('1')
        method = boards().input('board', root.get_id())
        method.parameters()
        viewer = MagicMock()
        viewer.is_staff.return_value = False
        viewer.is_authenticated.return_value = False
        with patch.object(GDO_User, 'current', return_value=viewer):
            self.assertEqual([], method.board_actions().get_fields())
            self.assertNotIn('board_id', [header.get_name() for header in method.gdo_table_headers()])
            viewer.is_authenticated.return_value = True
            self.assertEqual(['new_thread'], [action.get_name() for action in method.board_actions().get_fields()])
            with patch.object(GDO_ForumBoard, 'is_thread_allowed', return_value=False):
                self.assertEqual([], method.board_actions().get_fields())
            viewer.is_staff.return_value = True
            self.assertIsInstance(method.gdo_table_headers()[0], GDT_Button)
