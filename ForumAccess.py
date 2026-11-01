class ForumAccess:
    """Recheck board-scoped permissions before the framework's method cache."""

    def has_permission(self, user, display_error=True):
        if not self.gdo_has_permission(user):
            return False if not display_error else self.err_generic_permission()
        return super().has_permission(user, display_error)


class ForumStaffAccess:
    """Recheck staff access before the framework's method cache."""

    def has_permission(self, user, display_error=True):
        if not user.is_staff():
            return False if not display_error else self.err_permission('staff')
        if self._raw_args.get_val(self.crud_name(), None) and not self.crud_gdo():
            return False if not display_error else self.err_generic_permission()
        return super().has_permission(user, display_error)


class ForumPostForm:
    """Never execute a forum form action on an HTTP GET request."""

    def gdo_execute(self):
        from gdo.base.Application import Application
        if Application.IS_HTTP and Application.get_request_method() != 'POST':
            self.parameters()
            return self.render_page()
        return super().gdo_execute()
