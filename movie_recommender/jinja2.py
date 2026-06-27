from __future__ import annotations

from jinja2 import Environment


def environment(**options):
    from django.templatetags.static import static
    from django.urls import reverse
    from django.template.defaultfilters import date, floatformat

    env = Environment(**options)

    def url(viewname: str, *args, **kwargs) -> str:
        return reverse(viewname, args=args or None, kwargs=kwargs or None)

    env.globals.update({"static": static, "url": url})
    env.filters.update({"date": date, "floatformat": floatformat})
    return env
