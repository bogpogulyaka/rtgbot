from rtgbot.components.base import Component
from rtgbot.decorators import register_props


class For(Component):
    @register_props
    def __init__(self, items, reverse_order=False, **kwargs):
        super().__init__(**kwargs)

    async def render(self):
        items = list(enumerate(self.props.items))
        if self.props.reverse_order:
            items = reversed(items)

        return *[
            self.props.children[0](item, index) for index, item in items
        ],
