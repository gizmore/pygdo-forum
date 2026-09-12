from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.base.Query import Query
from gdo.forum import GDO_ForumBoard
from gdo.forum.GDO_ForumPost import GDO_ForumPost
from gdo.forum.GDO_ForumThread import GDO_ForumThread
from gdo.forum.GDT_Board import GDT_Board
from gdo.date.GDT_Created import GDT_Created
from gdo.date.Time import Time
from gdo.table.MethodQueryTable import MethodQueryTable
from gdo.ui.GDT_Link import GDT_Link


class threads(MethodQueryTable):
    """List the discussion threads belonging directly to one forum board."""

    def gdo_needs_authentication(self) -> bool:
        return False

    def gdo_has_permission(self, user) -> bool:
        return self.get_board().has_permission(user)

    def gdo_searched(self) -> bool:
        return False

    def gdo_filtered(self) -> bool:
        return False

    def gdo_ordered(self) -> bool:
        return False

    def gdo_parameters(self) -> list[GDT]:
        return [GDT_Board('board').not_null().initial('1')]

    def get_board(self) -> GDO_ForumBoard:
        return self.param_value('board')

    def gdo_table(self) -> GDO:
        return GDO_ForumThread.table()

    def gdo_table_query(self) -> Query:
        post_table = GDO_ForumPost.table().gdo_table_name()
        return super().gdo_table_query().where(
            f'thread_board={self.get_board().get_id()}'
        ).order(
            f'(SELECT MIN(post_created) FROM {post_table} WHERE post_thread=thread_id) ASC'
        )

    def gdo_table_headers(self) -> list[GDT]:
        table = self.gdo_table()
        return [
            GDT_Link('thread_title').label('title').icon(None),
            table.column('thread_created'),
            GDT_Link('last_post_date').label('last_post_date').icon(None),
            table.column('thread_creator'),
        ]

    def thread_href(self, thread: GDO_ForumThread, page: int = 1) -> str:
        return self.gdo_module().href(
            'thread',
            f'&title={thread.seo_title()}&id={thread.get_id()}&_p={max(1, page)}',
        )

    def render_thread_title(self, link: GDT_Link, thread: GDO_ForumThread) -> str:
        return link.href(self.thread_href(thread)).text_raw(thread.render_name()).render_html()

    def render_thread_created(self, date: GDT_Created, thread: GDO_ForumThread) -> str:
        return date.date_format(Time.FMT_BOTH_FULL).render_html()

    def render_last_post_date(self, link: GDT_Link, thread: GDO_ForumThread) -> str:
        if not (post := thread.get_last_post()):
            return ''
        page = ((thread.num_posts() - 1) // self.gdo_paginate_size()) + 1
        date = GDT_Created('last_post_date').val(post.gdo_val('post_created'))
        return link.href(self.thread_href(thread, page)).text_raw(
            date.render_html(), escaped=False
        ).render_html()
