from rtgbot.components.base import Component
from rtgbot.decorators import register_props
from rtgbot.components.widgets import Button, Text
from rtgbot.utils import expand_component_tree


class Checkbox(Component):
    @register_props
    def __init__(self,
                 checked=False,
                 on_change=None,
                 **kwargs):
        super().__init__(**kwargs)

    async def setup(self):
        def update_checked(checked, _):
            self.checked = checked

        def update_item_getter(children, _):
            if len(children) == 1:
                self.item_getter = children[0]
            elif len(children == 2):
                self.item_getter = lambda item, sel: sel and children[0] or children[1]
            else:
                self.item_getter = lambda item, sel: None

        self.checked = False
        self.rct.watch(lambda: self.props.checked, update_checked, immediate=True)
        self.rct.watch(lambda: self.props.children, update_item_getter, immediate=True)

    async def render(self):
        try:
            component = self.item_getter(self.checked, self._on_click)
        except:
            component = self.item_getter(self.checked)

        if isinstance(component, str | Text):
            return Button(on_click=self._on_click)(component)
        else:
            return Component()(tuple(expand_component_tree(component)))

    async def _on_click(self, e):
        self.checked = not self.checked

        if self.props.on_change:
            await self.props.on_change(self.checked)
