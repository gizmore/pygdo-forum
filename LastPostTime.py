from gdo.date.GDT_DateTime import GDT_DateTime
from gdo.date.Time import Time


def render_last_post_time(value: str) -> str:
    """Render a forum post timestamp to the minute with its relative age."""
    return GDT_DateTime('last_post_date').val(value).date_format(Time.FMT_BOTH_MINUTE).render_html()
