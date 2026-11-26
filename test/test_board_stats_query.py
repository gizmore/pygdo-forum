import unittest
from unittest.mock import MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Cache import Cache
from gdo.base.Render import Mode
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard
from gdo.forum.method.boards import boards


class BoardStatsQueryTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)
        Cache.init()
        self.table = GDO_ForumBoard.table()

    def test_permission_query_has_no_statistics(self):
        query = self.table.select('board_permission').where('board_id=1').build_query()
        self.assertIn('SELECT board_permission FROM', query)
        self.assertNotIn('last_post_date', query)
        self.assertNotIn('num_threads', query)

    def test_cached_board_permission_does_not_query_the_board_table(self):
        board = GDO_ForumBoard.blank({'board_id': '1', 'board_permission': None}, False)
        with patch.object(GDO_ForumBoard, 'select', side_effect=AssertionError('unexpected query')):
            self.assertTrue(board.has_permission(MagicMock()))
        self.assertTrue(board.gdo_persistent())

    def test_board_with_missing_permission_column_fails_closed(self):
        board = GDO_ForumBoard.blank({'board_id': '1'}, False)
        board._vals.pop('board_permission', None)
        self.assertFalse(board.has_permission(MagicMock()))

    def test_explicit_listing_includes_both_statistics(self):
        query = self.table.select_with_stats(self.table.select()).build_query()
        self.assertIn('AS last_post_date', query)
        self.assertIn('AS num_threads', query)

    def test_empty_board_listing_still_selects_statistics(self):
        method = boards()
        board = MagicMock()
        board.get_id.return_value = '1'
        with patch.object(method, 'get_board', return_value=board), \
                patch.object(method, 'gdo_table', return_value=self.table), \
                patch('gdo.base.Query.Query.exec') as execute:
            execute.return_value.fetch_assoc.return_value = None
            query = method.gdo_table_query().build_query()
        self.assertIn('AS last_post_date', query)
        self.assertIn('AS num_threads', query)

    def test_board_listing_selects_statistics_for_visible_children(self):
        method = boards()
        board = MagicMock()
        board.get_id.return_value = '1'
        bounds = MagicMock()
        bounds.fetch_assoc.return_value = {'board_tree_left': '1', 'board_tree_right': '4'}
        with patch.object(method, 'get_board', return_value=board), \
                patch.object(method, 'gdo_table', return_value=self.table), \
                patch('gdo.base.Query.Query.exec', side_effect=[bounds, []]):
            query = method.gdo_table_query().build_query()
        self.assertIn('AS last_post_date', query)
        self.assertIn('AS num_threads', query)
        self.assertIn('board_tree_left>1', query)
