from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.base.Query import Query
from gdo.base.Application import Application
from gdo.base.Cache import Cache
from gdo.core.GDT_AutoInc import GDT_AutoInc
from gdo.core.GDT_Bool import GDT_Bool
from gdo.core.GDT_Name import GDT_Name
from gdo.core.GDT_Permission import GDT_Permission
from gdo.core.GDT_Tree import GDT_Tree
from gdo.core.GDT_UInt import GDT_UInt
from gdo.core.GDT_Virtual import GDT_Virtual
from gdo.date.GDT_Date import GDT_Date
from gdo.ui.GDT_IconSelect import GDT_IconSelect
from gdo.ui.GDT_Title import GDT_Title


class GDO_ForumBoard(GDO):

    def gdo_columns(self) -> list[GDT]:
        from gdo.forum.GDO_ForumThread import GDO_ForumThread
        from gdo.forum.GDO_ForumPost import GDO_ForumPost
        table = GDO_ForumThread.table().gdo_table_name()
        posts = GDO_ForumPost.table().gdo_table_name()
        return [
            GDT_AutoInc('board_id'),
            GDT_Name('board_name').not_null().unique(),
            GDT_Title('board_title').not_null(),
            GDT_IconSelect('board_icon'),
            GDT_Permission('board_permission'),
            GDT_Bool('board_threads_allowed').not_null().initial('1'),
            GDT_Tree('board_tree').not_null(),
            GDT_Virtual(GDT_Date('last_post_date')).query(Query().table(posts).select('MAX(post_created)').where(f'post_thread IN (SELECT thread_id FROM {table} WHERE thread_board=gdo_forumboard.board_id AND thread_deleted IS NULL)')).auto_select(True),
            GDT_Virtual(GDT_UInt('num_threads')).query(Query().table(table).select('COUNT(*)').where('thread_board=gdo_forumboard.board_id AND thread_deleted IS NULL')).auto_select(True),
        ]

    def render_name(self):
        return self.gdo_val('board_title')

    def get_left(self) -> str:
        return self.gdo_val('board_tree_left')

    def get_right(self) -> str:
        return self.gdo_val('board_tree_right')

    def num_posts(self) -> int:
        """Return the number of posts in threads directly in this board."""
        return self.post_stats()[0]

    def num_replies(self) -> int:
        """Return posts excluding one opening post per thread."""
        posts, threads_with_posts, _ = self.post_stats()
        return posts - threads_with_posts

    def last_post_date(self) -> str | None:
        """Return the most recent post date in this board, if any."""
        return self.post_stats()[2]

    def post_stats(self) -> tuple[int, int, str | None]:
        """Return posts, threads with posts, and the latest post date."""
        from gdo.forum.GDO_ForumPost import GDO_ForumPost
        from gdo.forum.GDO_ForumThread import GDO_ForumThread

        posts = GDO_ForumPost.table().gdo_table_name()
        threads = GDO_ForumThread.table().gdo_table_name()
        row = Application.db().select(
            f'SELECT COUNT(post.post_id), COUNT(DISTINCT post.post_thread), '
            f'MAX(post.post_created) FROM {threads} AS thread '
            f'LEFT JOIN {posts} AS post ON post.post_thread=thread.thread_id '
            f'WHERE thread.thread_board={self.get_id()} AND thread.thread_deleted IS NULL',
            False,
        ).fetch_row()
        return int(row[0] or 0), int(row[1] or 0), row[2]

    def is_thread_allowed(self) -> bool:
        if not self.is_persisted() or not self.get_id():
            return False
        row = self.table().select('board_threads_allowed').where(f'board_id={int(self.get_id())}').nocache().exec().fetch_assoc()
        return bool(row and str(row['board_threads_allowed']) == '1')

    def has_permission(self, user) -> bool:
        """Whether ``user`` may view content in this board.

        An empty permission deliberately means public access.  A selected
        permission is checked through the central permission model.
        """
        if not self.is_persisted() or not self.get_id():
            return False
        row = self.table().select('board_permission').where(f'board_id={int(self.get_id())}').nocache().exec().fetch_assoc()
        if row is None:
            return False
        permission_id = row['board_permission']
        if permission_id is None:
            return True
        from gdo.core.GDO_Permission import GDO_Permission
        permission = GDO_Permission.table().get_by_aid(str(permission_id))
        return bool(permission and GDO_Permission.has_permission(user, permission.get_name()))

    def parent(self) -> 'GDO_ForumBoard | None':
        if not self.get_id():
            return None
        current = self.table().select('board_tree_left, board_tree_right').where(
            f'board_id={int(self.get_id())}'
        ).nocache().exec().fetch_assoc()
        if not current:
            return None
        left, right = int(current['board_tree_left']), int(current['board_tree_right'])
        return (self.table().select().where(
            f'board_tree_left<{left} AND board_tree_right>{right}'
        ).order('board_tree_right-board_tree_left').first().nocache().exec().fetch_object())

    @classmethod
    def lock_tree(cls) -> dict[str, tuple[int, int]]:
        """Read and lock the current tree until the caller commits."""
        result = Application.db().select(
            f'SELECT board_id, board_tree_left, board_tree_right FROM {cls.table().gdo_table_name()} '
            'ORDER BY board_id FOR UPDATE', False)
        rows = {}
        while row := result.fetch_row():
            rows[str(row[0])] = (int(row[1]), int(row[2]))
        return rows

    @classmethod
    def create_child(cls, parent: 'GDO_ForumBoard', title: str,
                     icon: str = None, permission: str = None,
                     name: str = None, threads_allowed: str = '1') -> 'GDO_ForumBoard':
        """Append a board as the last child of ``parent``.

        The method owns the nested-set update, so callers never write tree
        boundaries directly.
        """
        rows = cls.lock_tree()
        if parent.get_id() not in rows:
            raise ValueError('The parent board no longer exists.')
        position = rows[parent.get_id()][1]
        table = cls.table()
        table_name = table.gdo_table_name()

        Application.db().query(
            f'UPDATE {table_name} SET board_tree_right=board_tree_right+2 '
            f'WHERE board_tree_right>={position}'
        )
        Application.db().query(
            f'UPDATE {table_name} SET board_tree_left=board_tree_left+2 '
            f'WHERE board_tree_left>{position}'
        )
        # The insertion also grows every ancestor. Synchronize each cached
        # board affected by the SQL update, not just the selected parent.
        for cached in Cache.OCACHE.get(table_name, {}).values():
            if cached.get_id() not in rows:
                continue
            cached_tree = cached.column('board_tree')
            cached_left, cached_right = rows[cached.get_id()]
            cached_tree.set((cached_left + (2 if cached_left > position else 0),
                             cached_right + (2 if cached_right >= position else 0)))
            Cache.update_for(cached)
        return cls.blank({
            'board_name': name or title.lower().replace(' ', '-'),
            'board_title': title,
            'board_icon': icon,
            'board_permission': permission,
            'board_threads_allowed': threads_allowed,
            'board_tree_left': str(position),
            'board_tree_right': str(position + 1),
        }).insert()

    def move_to(self, parent: 'GDO_ForumBoard') -> 'GDO_ForumBoard':
        """Move this subtree below ``parent`` and rebuild nested-set bounds."""
        rows = self.lock_tree()
        if self.get_id() not in rows or parent.get_id() not in rows:
            raise ValueError('The board or its parent no longer exists.')
        children: dict[str | None, list[str]] = {None: []}
        parents: dict[str, str | None] = {}
        stack = []
        for board_id in sorted(rows, key=lambda key: rows[key][0]):
            left, right = rows[board_id]
            while stack and left > stack[-1][1]:
                stack.pop()
            parent_id = stack[-1][0] if stack else None
            parents[board_id] = parent_id
            children.setdefault(parent_id, []).append(board_id)
            children.setdefault(board_id, [])
            stack.append((board_id, right))

        if parents[self.get_id()] is None:
            raise ValueError('The root board cannot be moved.')
        if parents[self.get_id()] == parent.get_id():
            return self

        descendant_ids = set()
        pending = [self.get_id()]
        while pending:
            board_id = pending.pop()
            descendant_ids.add(board_id)
            pending.extend(children[board_id])
        if parent.get_id() in descendant_ids:
            raise ValueError('A board cannot be moved below itself.')

        old_parent_id = parents[self.get_id()]
        children[old_parent_id].remove(self.get_id())
        children[parent.get_id()].append(self.get_id())

        bounds = {}
        next_bound = 1

        def visit(board_id: str):
            nonlocal next_bound
            left = next_bound
            next_bound += 1
            for child_id in children[board_id]:
                visit(child_id)
            bounds[board_id] = (left, next_bound)
            next_bound += 1

        for board_id in children[None]:
            visit(board_id)
        table_name = self.gdo_table_name()
        for board_id in rows:
            left, right = bounds[board_id]
            Application.db().query(
                f'UPDATE {table_name} SET board_tree_left={left}, board_tree_right={right} '
                f'WHERE board_id={int(board_id)}'
            )
            cached = Cache.OCACHE.get(table_name, {}).get(board_id)
            if cached:
                cached.column('board_tree').set((left, right))
                Cache.update_for(cached)
        return self
