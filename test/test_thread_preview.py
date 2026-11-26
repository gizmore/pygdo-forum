import unittest
from unittest.mock import MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Method import Method
from gdo.base.Render import Mode
from gdo.forum.method.thread import thread


class ThreadPreviewTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_html)
        self.method = thread()
        self.method._env_user = MagicMock()
        self.discussion = MagicMock()
        self.discussion.gdo_val.return_value = None
        self.discussion.get_board.return_value.has_permission.return_value = True
        self.discussion.render_name.return_value = 'A "funny" <title>'
        self.discussion.get_id.return_value = '12'
        self.method.param_value = MagicMock(return_value=self.discussion)

    def test_title_and_opening_message_are_escaped_and_trimmed(self):
        post = MagicMock()
        post.render_message.return_value = 'Hello\nworld & "friends"'
        query = MagicMock()
        query.select.return_value.where.return_value.order.return_value.first.return_value.exec.return_value.fetch_object.return_value = post
        with patch('gdo.forum.method.thread.GDO_ForumPost.table', return_value=query):
            self.assertEqual('A &quot;funny&quot; &lt;title&gt;', self.method.gdo_render_title())
            self.assertEqual('Hello world &amp; &quot;friends&quot;', self.method.gdo_render_descr())
        query.select.return_value.where.return_value.order.assert_called_once_with('post_created ASC, post_id ASC')

    def test_description_is_capped_before_escaping(self):
        post = MagicMock()
        post.render_message.return_value = 'x' * 250
        query = MagicMock()
        query.select.return_value.where.return_value.order.return_value.first.return_value.exec.return_value.fetch_object.return_value = post
        self.discussion.render_name.return_value = 'Title'
        with patch('gdo.forum.method.thread.GDO_ForumPost.table', return_value=query):
            description = self.method.gdo_render_descr()
        self.assertEqual(200, len(description))
        self.assertEqual('x' * 200, description)

    def test_private_board_does_not_expose_metadata(self):
        self.discussion.get_board.return_value.has_permission.return_value = False
        with patch.object(Method, 'gdo_render_title', return_value='Thread'), \
             patch.object(Method, 'gdo_render_descr', return_value='Read a forum discussion.'), \
             patch('gdo.forum.method.thread.GDO_ForumPost.table') as table:
            self.assertEqual('Thread', self.method.gdo_render_title())
            self.assertEqual('Read a forum discussion.', self.method.gdo_render_descr())
        table.assert_not_called()
