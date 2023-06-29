import math

from rtgbot.components.base import Component
from rtgbot.components.conditional import Show, Yes, No
from rtgbot.decorators import register_props

from rtgbot.components.for_each import For
from rtgbot.components.widgets import Button
from rtgbot.components.layout import Row, Group


class Paginator(Component):
    @register_props
    def __init__(self, count: int, visible_count=5, page: int = None, on_page_changed=None, max_rows=1, **kwargs):
        super().__init__(**kwargs)

    async def setup(self):
        def watch_page(page, _):
            if page:
                self.page = page

        self.page = 1
        self.rct.watch(lambda: self.props.page, watch_page, immediate=True)

    async def render(self):
        def fpage(page):
            if page is None:
                return "..."
            else:
                return page == self.page and f"[ {page} ]" or str(page)

        page = self.page
        count = self.props.count
        visible_count = self.props.visible_count

        if visible_count > 8:
            rows_cnt = self.props.max_rows
            if count >= 8 * rows_cnt:
                visible_count = 8 * rows_cnt
            else:
                visible_count = math.ceil(count / rows_cnt) * rows_cnt

        all_fit = count <= visible_count

        if all_fit:
            displayed_indices = list(range(1, count + 1))
        else:

            if page <= visible_count // 2 + 1:
                displayed_indices = list(range(1, visible_count)) + [count]
            elif page >= count - (visible_count - 1) // 2:
                displayed_indices = [1] + list(range(count - visible_count + 2, count + 1))
            else:
                displayed_indices = [1] + list(range(page - (visible_count - 2) // 2, page + (visible_count - 3) // 2 + 1)) + [count]

        btn_prev = Button(on_click=self.prev)(page > 1 and 'ᐊ' or '|')
        btn_next = Button(on_click=self.next)(page < count and 'ᐅ' or '|')
        btn_pages = For(items=displayed_indices)(
            lambda page_id, _: Button(on_click=self.select_page(page_id))(fpage(page_id))
        ),

        return Show(visible_count <= 6)(
            Yes()(
                Row()(
                    btn_prev,
                    btn_pages,
                    btn_next
                )
            ),
            No()(
                Group(width=visible_count, fill_tail=True, fill_evenly=True)(
                    btn_pages
                ),
                Row()(
                    btn_prev,
                    btn_next
                )
            )
        )

    async def prev(self, e):
        if self.page > 1:
            self.page -= 1
            if self.props.on_page_changed:
                await self.props.on_page_changed(self.page)

    async def next(self, e):
        if self.page < self.props.count:
            self.page += 1
            if self.props.on_page_changed:
                await self.props.on_page_changed(self.page)

    def select_page(self, page):
        async def process_event(e):
            if page is not None and 1 <= page <= self.props.count:
                prev_page = self.page
                self.page = page

                if self.props.on_page_changed and page != prev_page:
                    await self.props.on_page_changed(page)
        return process_event
