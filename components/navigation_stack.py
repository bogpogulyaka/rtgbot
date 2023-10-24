from rtgbot.components.base import Window, WindowsGroup, Component
from rtgbot.components.for_each import For
from rtgbot.decorators import register_props


class NavigationStack(WindowsGroup):
    @register_props
    def __init__(self):
        super().__init__()

    async def render(self):
        stack = self.context.navigator.stack

        return For(stack)(
            lambda group, i: Component(visible=i == len(stack) - 1)(group[0])
        )
