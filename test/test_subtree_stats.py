import unittest
from unittest.mock import MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.forum.method.boards import boards


def board(identifier, left, right, allowed=True):
    item = MagicMock()
    item.get_id.return_value = str(identifier)
    item.get_left.return_value = str(left)
    item.get_right.return_value = str(right)
    item.has_permission.return_value = allowed
    return item


class SubtreeStatsTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_hidden_board_and_its_descendants_are_excluded(self):
        root = board(1, 1, 12)
        parent = board(2, 2, 11)
        leaf = board(3, 3, 4)
        hidden = board(4, 5, 8, False)
        hidden_child = board(5, 6, 7)
        sibling = board(6, 9, 10)
        visible = boards.visible_tree([hidden_child, leaf, hidden, root, sibling, parent], object())
        self.assertEqual(['1', '2', '3', '6'], [item.get_id() for item in visible])

    def test_subtree_stats_uses_visible_ids_and_counts_replies(self):
        parent = board(2, 2, 11)
        visible = [board(1, 1, 12), parent, board(3, 3, 4), board(6, 9, 10)]
        method = boards()
        method._visible_tree = visible
        method._subtree_stats_cache = {}
        result = MagicMock()
        result.fetch_row.return_value = (3, 5, 2, '2026-11-26 12:00:00')
        db = MagicMock()
        db.select.return_value = result
        with patch('gdo.forum.method.boards.Application.db', return_value=db), \
                patch('gdo.forum.GDO_ForumPost.GDO_ForumPost.table') as posts, \
                patch('gdo.forum.GDO_ForumThread.GDO_ForumThread.table') as threads:
            posts.return_value.gdo_table_name.return_value = 'gdo_forumpost'
            threads.return_value.gdo_table_name.return_value = 'gdo_forumthread'
            self.assertEqual((3, 3, '2026-11-26 12:00:00'), method.subtree_stats(parent))
            self.assertEqual((3, 3, '2026-11-26 12:00:00'), method.subtree_stats(parent))
        self.assertIn('thread.thread_board IN (2,3,6)', db.select.call_args.args[0])
        self.assertEqual(1, db.select.call_count)
