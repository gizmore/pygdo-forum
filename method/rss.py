from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

from gdo.base.GDT import GDT
from gdo.base.Method import Method
from gdo.base.Render import Mode
from gdo.base.util.href import url
from gdo.core.GDT_Raw import GDT_Raw
from gdo.forum.GDO_ForumPost import GDO_ForumPost
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard
from gdo.forum.GDO_ForumThread import GDO_ForumThread


def xml_text(value: str) -> str:
    """Escape text and discard characters forbidden in XML 1.0."""
    return escape(''.join(char for char in value if ord(char) in (9, 10, 13)
                          or 0x20 <= ord(char) <= 0xD7FF
                          or 0xE000 <= ord(char) <= 0xFFFD
                          or 0x10000 <= ord(char) <= 0x10FFFF))


class rss(Method):
    """Public RSS 2.0 feed of recent, readable forum activity."""

    @classmethod
    def gdo_trigger(cls) -> str:
        return 'forum.rss'

    def gdo_needs_authentication(self) -> bool:
        return False

    def gdo_method_hidden(self) -> bool:
        return True

    def gdo_execute(self) -> GDT:
        items = []
        feed_url = url('forum', 'rss', fmt='rss')
        board_ids = [int(board.get_id()) for board in GDO_ForumBoard.table().select().nocache().exec()
                     if board.has_permission(self._env_user)]
        threads = GDO_ForumThread.table().gdo_table_name()
        query = GDO_ForumPost.table().select().where(
            f"post_thread IN (SELECT thread_id FROM {threads} WHERE thread_deleted IS NULL AND thread_board IN ({','.join(map(str, board_ids)) or 'NULL'}))"
        ).order('post_created DESC, post_id DESC').limit(20)
        for post in query.exec():
            thread = post.column('post_thread').get_value()
            if not thread or not (board := thread.get_board()) or not board.has_permission(self._env_user):
                continue
            post_id = int(post.get_id())
            page = post.thread_page()
            href = url('forum', 'thread', f'&title={thread.seo_title()}&id={thread.get_id()}&_p={page}') + f'#forum-post-{post_id}'
            created = post.gdo_val('post_created')
            published = format_datetime(datetime.fromisoformat(created).replace(tzinfo=timezone.utc), usegmt=True)
            description = xml_text(post.render_message(Mode.render_txt))
            items.append(
                f'<item><title>{xml_text(thread.render_name())}</title><link>{escape(href)}</link>'
                f'<description>{description}</description>'
                f'<guid isPermaLink="false">{escape(feed_url)}#forum-post-{post_id}</guid><pubDate>{published}</pubDate></item>'
            )
            if len(items) == 20:
                break
        forum_url = url('forum', 'forum', '&id=1')
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<rss version="2.0"><channel>'
            '<title>Forum Activity</title>'
            f'<link>{escape(forum_url)}</link><description>Recent forum activity</description>'
            f'<atom:link xmlns:atom="http://www.w3.org/2005/Atom" href="{escape(feed_url)}" rel="self" type="application/rss+xml"/>'
            f'{"".join(items)}</channel></rss>'
        )
        return GDT_Raw('rss').val(xml)
