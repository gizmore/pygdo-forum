from gdo.core.GDT_ObjectSelect import GDT_ObjectSelect
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard


class GDT_ForumBoard(GDT_ObjectSelect):
    """Forum-board selector rendered in nested-set order as an ASCII tree."""

    def __init__(self, name: str):
        super().__init__(name)
        self.table(GDO_ForumBoard.table())
        self._child = None

    def for_child(self, board: GDO_ForumBoard):
        """Exclude a board and its descendants from its possible parents."""
        self._child = board
        return self

    def gdo_choices(self) -> dict[str, str]:
        boards = self._table.select().order('board_tree_left').exec().fetch_all()
        choices = {}
        stack = []
        for board in boards:
            left, right = board.column('board_tree').get_value()
            while stack and left > stack[-1]:
                stack.pop()
            depth = len(stack)
            if not self._child or not (
                self._child.column('board_tree').get_left() <= left and
                right <= self._child.column('board_tree').get_right()
            ):
                choices[board.get_id()] = f"{'|  ' * depth}+-- {board.render_name()}"
            stack.append(right)
        return choices

    def to_value(self, val: str):
        if val is None or val == '':
            return None
        choices = self.init_choices()
        if val in choices:
            return self._table.get_by_aid(val)
        matches = [key for key, label in choices.items() if label.lower().endswith(val.lower())]
        return self._table.get_by_aid(matches[0]) if len(matches) == 1 else None
