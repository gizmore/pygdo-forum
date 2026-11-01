from gdo.core.GDT_ObjectSelect import GDT_ObjectSelect
from gdo.forum.GDO_ForumBoard import GDO_ForumBoard


class GDT_ForumBoard(GDT_ObjectSelect):
    """Forum-board selector rendered in nested-set order as an ASCII tree."""

    def __init__(self, name: str):
        super().__init__(name)
        self.table(GDO_ForumBoard.table())
        self._child = None
        self._viewer = None

    def visible_to(self, user):
        """Limit choices and name lookup to boards readable by this user."""
        self._viewer = user
        return self

    def for_child(self, board: GDO_ForumBoard):
        """Exclude a board and its descendants from its possible parents."""
        self._child = board
        return self

    def init_choices(self):
        # A reused selector must not retain old permissions or tree positions.
        if hasattr(self, '_choices'):
            del self._choices
        return super().init_choices()

    def gdo_choices(self) -> dict[str, str]:
        boards = self._table.select().order('board_tree_left').nocache().exec().fetch_all()
        child_bounds = None
        if self._child:
            child_bounds = next((board.column('board_tree').get_value() for board in boards
                                 if board.get_id() == self._child.get_id()), None)
            if child_bounds is None:
                return {}
        choices = {}
        stack = []
        for board in boards:
            left, right = board.column('board_tree').get_value()
            while stack and left > stack[-1]:
                stack.pop()
            depth = len(stack)
            if (self._viewer is None or board.has_permission(self._viewer)) and (not child_bounds or not (
                child_bounds[0] <= left and right <= child_bounds[1]
            )):
                choices[board.get_id()] = f"{'|  ' * depth}+-- {board.render_name()}"
            stack.append(right)
        return choices

    def to_value(self, val: str):
        if val is None or val == '':
            return None
        choices = self.init_choices()
        if val in choices:
            return self._table.get_by_aid(val)
        if board := self._table.get_by_vals({'board_name': val}):
            return board if board.get_id() in choices else None
        matches = [key for key, label in choices.items() if label.lower().endswith(val.lower())]
        return self._table.get_by_aid(matches[0]) if len(matches) == 1 else None
