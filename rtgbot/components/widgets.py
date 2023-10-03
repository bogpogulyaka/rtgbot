import typing as tp

from aiogram.enums import ContentType, InputMediaType

from rtgbot.components.base import Component
from rtgbot.decorators import register_props
from rtgbot.etities.dom import ButtonElement, InputElement, MediaElement
from rtgbot.etities.event import ButtonClickEvent, MessageInputEvent
from rtgbot.utils import Symbols


class Text(Component):
    @register_props
    def __init__(self, text='', end='\n', trim_spaces=False, **kwargs):
        super().__init__(**kwargs)

    def render_text(self):
        text = self.props.text

        if not self.props.trim_spaces:
            text = Symbols.ZW + text + Symbols.ZW

        text += self.props.end

        return text


class Button(Component):
    @register_props
    def __init__(self, on_click: tp.Callable[[ButtonClickEvent], tp.Awaitable] = None, url='', **kwargs):
        super().__init__(**kwargs)

    def render_text(self):
        pass

    def render_kbd(self):
        try:
            text = super().render_text()\
                .replace('\n', '').replace(Symbols.ZW, '')\
                .replace('&lt;', '<').replace('&gt;', '>')

            if text == '':
                text = Symbols.EMPTY
        except Exception as e:
            text = "<btn>"

        return [[ButtonElement(
            tree_node=self,
            text=text,
            url=self.props.url,
            callback=self.props.on_click,
        )]]

    async def on_event(self, event: ButtonClickEvent):
        if event.sender == self and self.props.on_click:
            await self.props.on_click(event)


class MessageInput(Component):
    @register_props
    def __init__(self,
                 content_types: tp.Union[tp.Sequence[str], str] = ContentType.ANY,
                 on_input: tp.Callable = None,
                 **kwargs):
        super().__init__(**kwargs)

    def render_inputs(self):
        return [InputElement(
            tree_node=self,
            content_types=self.props.content_types,
            callback=self.props.on_input
        )]

    async def on_event(self, event: MessageInputEvent):
        if event.sender == self and self.props.on_input:
            await self.props.on_input(event)


class StaticMedia(Component):
    @register_props
    def __init__(self,
                 url: str = None,
                 path: str = None,
                 type: str = InputMediaType.PHOTO,
                 **kwargs):
        super().__init__(**kwargs)

    def render_media(self):
        if not (self.props.url or self.props.path):
            return []

        return [MediaElement(
            tree_node=self,
            url=self.props.url,
            path=self.props.path,
            type=self.props.type
        )]


class BadComponent(Component):
    @register_props
    def __init__(self, info=''):
        super().__init__()

    def render_text(self):
        info = str(self.props.info).replace('<', '&lt;').replace('>', '&gt;')
        return f"{{ bad component: {info} }}\n"


class ExceptionComponent(Component):
    @register_props
    def __init__(self, e: Exception):
        super().__init__()

    def render_text(self):
        info = str(self.props.e).replace('<', '&lt;').replace('>', '&gt;')
        return f"{{ exception: {info} }}\n"
