from rtgbot.components.base import Component
from rtgbot.decorators import register_props
from rtgbot.components.for_each import For
from rtgbot.components.widgets import Button, Text
from rtgbot.components.layout import Group
from rtgbot.utils import expand_component_tree


class Select(Component):
    @register_props
    def __init__(self,
                 options,
                 value=None,
                 on_select=None,
                 unselect=False,
                 same_select=False,
                 width=None, max_width=None, fill_tail=True,
                 **kwargs):
        super().__init__(**kwargs)

    async def setup(self):
        def update_value(value, _):
            self.value = value

        def update_item_getter(children, _):
            if len(children) == 1:
                self.item_getter = children[0]
            elif len(children == 2):
                self.item_getter = lambda item, sel: sel and children[0] or children[1]
            else:
                self.item_getter = lambda item, sel: None

        self.value = None
        self.rct.watch(lambda: self.props.value, update_value, immediate=True)
        self.rct.watch(lambda: self.props.children, update_item_getter, immediate=True)

    async def render(self):
        def get_item_component(item, i):
            try:
                component = self.item_getter(item, self.value == item, self._on_select(item, i))
            except:
                component = self.item_getter(item, self.value == item)

            if isinstance(component, str | Text):
                return Button(on_click=self._on_select(item, i))(component)
            else:
                return Component()(tuple(expand_component_tree(component)))

        width = self.props.width
        max_width = self.props.max_width

        if width is None and max_width is None:
            width = 9999

        return Group(width=width, max_width=max_width, fill_tail=self.props.fill_tail)(
            For(items=self.props.options)(
                lambda item, i: get_item_component(item, i)
            )
        )

    def _on_select(self, item, item_id):
        async def handle_event(e=None):
            def set_selected():
                self.value = item
                self.selected_option_id = item_id

            if self.value == item:
                if self.props.unselect:
                    self.value = None
                    self.selected_option_id = None
                else:
                    if self.props.same_select:
                        set_selected()
                    else:
                        return
            else:
                set_selected()

            self.invalidate()
            if self.props.on_select:
                await self.props.on_select(self.value, self.selected_option_id)
        return handle_event
