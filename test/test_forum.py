import os

from gdo.base.Application import Application
from gdo.base.ModuleLoader import ModuleLoader
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard
from gdo.forum.GDO_ForumPost import GDO_ForumPost
from gdo.forum.GDO_ForumThread import GDO_ForumThread
from gdotest.TestUtil import GDOTestCase, reinstall_module
from gdotest.TestUtil import cli_gizmore, cli_plug


class ForumTest(GDOTestCase):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        Application.init(os.path.dirname(__file__ + "/../../../../"))
        loader = ModuleLoader.instance()
        loader.load_modules_db(True)
        reinstall_module('forum')
        Application.init_cli()
        loader.init_modules(True, True)
        loader.init_cli()

    async def test_install(self):
        pass

    async def test_chat_thread_marks_it_read(self):
        """Chat users only need reading state, not forum administration."""
        user = cli_gizmore()
        board = GDO_ForumBoard.table().get_by_aid('1')
        thread = GDO_ForumThread.blank({
            'thread_board': board.get_id(),
            'thread_title': 'Chat-first forum thread',
        }).insert()
        GDO_ForumPost.blank({
            'post_thread': thread.get_id(),
            'post_message_input': 'A post that starts out unread.',
        }).insert()

        unread = cli_plug(user, '$forum.unread')
        self.assertIn('Chat-first forum thread', unread)

        opened = cli_plug(user, f'$forum.thread {thread.get_id()}')
        self.assertIn('A post that starts out unread.', opened)
        self.assertNotIn('Invalid value', opened)

        unread = cli_plug(user, '$forum.unread')
        self.assertNotIn('Chat-first forum thread', unread)

    async def test_chat_lists_boards_and_replies(self):
        user = cli_gizmore()
        root = GDO_ForumBoard.table().get_by_aid('1')
        board = GDO_ForumBoard.blank({
            'board_parent': root.get_id(),
            'board_title': 'Chat board',
        }).insert()
        thread = GDO_ForumThread.blank({
            'thread_board': board.get_id(),
            'thread_title': 'Reply from chat',
        }).insert()
        GDO_ForumPost.blank({
            'post_thread': thread.get_id(),
            'post_message_input': 'Initial forum post.',
        }).insert()

        boards = cli_plug(user, '$forum.boards')
        self.assertIn('Chat board', boards)

        board_threads = cli_plug(user, f'$forum.board {board.get_id()}')
        self.assertIn('Reply from chat', board_threads)

        reply = cli_plug(user, f'$forum.reply {thread.get_id()} "Reply sent from chat."')
        self.assertIn('Reply', reply)
        thread_text = cli_plug(user, f'$forum.thread {thread.get_id()}')
        self.assertIn('Reply sent from chat.', thread_text)
        self.assertNotIn('Invalid value', thread_text)
