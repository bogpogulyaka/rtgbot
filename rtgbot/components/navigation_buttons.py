from typing import Callable

from rtgbot.components.base import Component, Window, WindowsGroup
from rtgbot.decorators import register_props
from rtgbot.components.widgets import Button
from rtgbot.navigator import NavigationMode


class Navigate(Component):
    @register_props
    def __init__(self,
                 to: Callable[[], Window | WindowsGroup] = None, state=None,
                 mode=NavigationMode.default, replace=False,
                 on_click=None,
                 **kwargs):
        super().__init__(**kwargs)

    async def render(self):
        return Button(on_click=self.on_click)(*self.props.children)

    async def on_click(self, e):
        if self.props.on_click:
            await self.props.on_click(e)

        self.context.navigator.navigate(
            to=self.props.to, state=self.props.state,
            mode=self.props.mode,
            replace=self.props.replace
            # add_to_stack=self.props.add_to_stack
        )


class Back(Component):
    @register_props
    def __init__(self,
                 to: str = None, state=None,
                 on_click=None,
                 **kwargs):
        super().__init__(**kwargs)

    async def render(self):
        return Button(on_click=self.on_click)(*self.props.children)

    async def on_click(self, e):
        if self.props.on_click:
            await self.props.on_click(e)
        self.context.navigator.back(to=self.props.to, state=self.props.state)
