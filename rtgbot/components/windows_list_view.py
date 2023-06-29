import inspect
import typing

from rtgbot.components.base import WindowsGroup, WindowChildren, Window
from rtgbot.components.for_each import For
from rtgbot.components.paginator import Paginator
from rtgbot.decorators import register_props


class WindowsListView(WindowsGroup):
    @register_props
    def __init__(self,
                 items_getter, item_builder,
                 items_count: int, page_size: int, paginator_width=5,
                 reverse_index=False, reverse_page_items=False,
                 header: WindowChildren = None, footer: WindowChildren = None,
                 show_header_paginator=True, show_footer_paginator=True,
                 page: int = None, on_page_changed=None,
                 **kwargs):
        super().__init__(**kwargs)

    async def setup(self):
        def watch_page(page, _):
            if page:
                self.page = page

        self.page = 1
        self.rct.watch(lambda: self.props.page, watch_page, immediate=True)

    async def render(self):
        props = self.props

        pages = (props.items_count - 1) // props.page_size + 1
        start = (self.page - 1) * props.page_size
        end = min(self.page * props.page_size, props.items_count)

        def get_index(index):
            return props.items_count - 1 - index if props.reverse_index else index

        return WindowsGroup()(
            Window(when=props.header is not None, key="header")(
                Paginator(when=self.props.show_header_paginator and pages > 1,
                          count=pages, visible_count=props.paginator_width, page=self.page,
                          on_page_changed=self._on_page_changed),
                props.header
            ),
            For(items=await self._get_items(start, end), reverse_order=self.props.reverse_page_items)(
                lambda item, i: props.item_builder(item, get_index(i + start))
            ),
            Window(when=props.footer is not None, key="footer")(
                Paginator(when=self.props.show_footer_paginator and pages > 1,
                          count=pages, visible_count=props.paginator_width, page=self.page,
                          on_page_changed=self._on_page_changed),
                props.footer
            ),
        )

    async def _on_page_changed(self, page):
        prev_page = self.page
        self.page = page

        if self.props.on_page_changed and page != prev_page:
            await self.props.on_page_changed(page)

    async def _get_items(self, start, end):
        func = self.props.items_getter

        if inspect.iscoroutinefunction(func):
            return await func(start, end)
        else:
            return func(start, end)
