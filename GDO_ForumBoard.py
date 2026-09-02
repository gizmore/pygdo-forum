from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.base.Application import Application
from gdo.core.GDT_AutoInc import GDT_AutoInc
from gdo.core.GDT_Tree import GDT_Tree
from gdo.ui.GDT_Title import GDT_Title


class GDO_ForumBoard(GDO):

    def gdo_columns(self) -> list[GDT]:
        return [
            GDT_AutoInc('board_id'),
            GDT_Title('board_title').not_null(),
            GDT_Tree('board_tree').not_null(),
        ]

    def render_name(self):
        return self.gdo_val('board_title')

    def num_posts(self) -> int:
        """Number of posts below this board.

        Posts are introduced after the board tree; keeping the query behind
        this method lets the navigation stay stable in the meantime.
        """
        return 0

    def parent(self) -> 'GDO_ForumBoard | None':
        left, right = self.column('board_tree').get_value()
        return (self.table().select().where(
            f'board_tree_left<{left} AND board_tree_right>{right}'
        ).order('board_tree_right-board_tree_left').first().exec().fetch_object())

    @classmethod
    def create_child(cls, parent: 'GDO_ForumBoard', title: str) -> 'GDO_ForumBoard':
        """Append a board as the last child of ``parent``.

        The method owns the nested-set update, so callers never write tree
        boundaries directly.
        """
        tree = parent.column('board_tree')
        position = tree.get_right()
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
        # Keep the caller's selected parent coherent for this request.
        tree.set_right(position + 2)
        return cls.blank({
            'board_title': title,
            'board_tree_left': str(position),
            'board_tree_right': str(position + 1),
        }).insert()

    def move_to(self, parent: 'GDO_ForumBoard') -> 'GDO_ForumBoard':
        """Move this subtree below ``parent`` and rebuild nested-set bounds."""
        old_parent = self.parent()
        if old_parent and old_parent.get_id() == parent.get_id():
            return self
        if old_parent is None:
            raise ValueError('The root board cannot be moved.')

        boards = self.table().select().order('board_tree_left').exec().fetch_all()
        children: dict[str | None, list[str]] = {None: []}
        parents: dict[str, str | None] = {}
        stack = []
        for board in boards:
            left, _ = board.column('board_tree').get_value()
            while stack and left > stack[-1].column('board_tree').get_right():
                stack.pop()
            parent_id = stack[-1].get_id() if stack else None
            parents[board.get_id()] = parent_id
            children.setdefault(parent_id, []).append(board.get_id())
            children.setdefault(board.get_id(), [])
            stack.append(board)

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
        for board in boards:
            left, right = bounds[board.get_id()]
            Application.db().query(
                f'UPDATE {table_name} SET board_tree_left={left}, board_tree_right={right} '
                f'WHERE board_id={board.get_id()}'
            )
            board.column('board_tree').set((left, right))
        return self
