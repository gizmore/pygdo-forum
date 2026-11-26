import unittest
from unittest.mock import MagicMock, patch

from gdo.date.Time import Time
from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.forum.LastPostTime import render_last_post_time
from gdo.forum.method.boards import boards


class LastPostTimeTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_html)

    def test_timestamp_uses_short_format_and_relative_age(self):
        with patch('gdo.ui.WithIcon.t', side_effect=lambda key: key), \
             patch.object(Time, 'display_date', return_value='11/20/2026 18:21') as date, \
             patch.object(Time, 'get_time', return_value=12345), \
             patch.object(Time, 'get_time_ago', return_value=3600), \
             patch.object(Time, 'human_duration', return_value='1h'), \
             patch('gdo.date.GDT_Timestamp.t', return_value='1h ago'):
            result = render_last_post_time('2026-11-20 18:21:41')
        self.assertIn('11/20/2026 18:21', result)
        self.assertIn('(1h ago)', result)
        self.assertIn('data-ts="12345"', result)
        date.assert_any_call('2026-11-20 18:21:41.000', Time.FMT_SHORT)

    def test_board_uses_last_post_timestamp(self):
        board = MagicMock()
        board.gdo_val.return_value = '2026-11-20 18:21:41'
        with patch('gdo.forum.method.boards.render_last_post_time', return_value='formatted'):
            self.assertEqual('formatted', boards().render_last_post_date(MagicMock(), board))
