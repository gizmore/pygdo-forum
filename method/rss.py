from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

from gdo.base.GDT import GDT
from gdo.base.Method import Method
from gdo.base.util.href import url
from gdo.core.GDT_Raw import GDT_Raw
from gdo.forum.GDO_ForumPost import GDO_ForumPost


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
        for post in GDO_ForumPost.table().select().order('post_created DESC, post_id DESC').limit(50).exec():
            thread = post.column('post_thread').get_value()
            if not thread.get_board().has_permission(self._env_user):
                continue
            href = url('forum', 'thread', f'&title={thread.seo_title()}&id={thread.get_id()}&_p=1')
            created = post.gdo_val('post_created')
            published = format_datetime(datetime.fromisoformat(created).replace(tzinfo=timezone.utc), usegmt=True)
            items.append(
                f'<item><title>{escape(thread.render_name())}</title><link>{escape(href)}</link>'
                f'<guid isPermaLink="true">{escape(href)}</guid><pubDate>{published}</pubDate></item>'
            )
            if len(items) == 20:
                break
        feed_url = url('forum', 'rss', fmt='rss')
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
