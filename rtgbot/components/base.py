from aiogram import types
from aiogram.enums import ParseMode
import typing as tp

from rtgbot.base import ComponentTreeNode
from rtgbot.decorators import register_props
from rtgbot.etities.dom import KeyboardData, MessageElement, DOM, InputElement, MediaElement


class Component(ComponentTreeNode):
    @register_props
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def render_media(self) -> tp.List[MediaElement]:
        media = []

        for child in self.rendered_children.values():
            child_media = child.render_media()
            if child_media:
                media.extend(child_media)

        return media

    def render_text(self) -> str:
        text = ""

        for child in self.rendered_children.values():
            child_text = child.render_text()
            if child_text:
                text += child_text

        return text

    def render_kbd(self) -> KeyboardData:
        kbd = []

        for child in self.rendered_children.values():
            child_kbd = child.render_kbd()
            if child_kbd:
                kbd.extend(child_kbd)

        return kbd

    def render_inputs(self) -> tp.List[InputElement]:
        inputs = []

        for child in self.rendered_children.values():
            child_inputs = child.render_inputs()
            if child_inputs:
                inputs.extend(child_inputs)

        return inputs


WindowChild = tp.Union['Window', Component, str]
WindowChildren = WindowChild | tp.Tuple[WindowChild, ...]


class Window(Component):
    @register_props
    def __init__(self,
                 route: str = None,
                 parse_mode: ParseMode = ParseMode.HTML,
                 disable_web_page_preview: bool = False,
                 enable_notification=False,
                 **kwargs):
        super().__init__(**kwargs)

    def render_message(self):
        return MessageElement(
            tree_node=self,
            media=self.render_media(),
            text=self.render_text(),
            keyboard=self.render_kbd(),
            inputs=self.render_inputs(),
            parse_mode=self.props.parse_mode,
            disable_web_page_preview=self.props.disable_web_page_preview,
            enable_notification=self.props.enable_notification
        )


WindowsGroupChild = tp.Union['WindowsGroup', Window | Component | str]
WindowsGroupChildren = WindowsGroupChild | tp.Tuple[WindowsGroupChild, ...]


class WindowsGroup(ComponentTreeNode):
    @register_props
    def __init__(self,
                 route: str = None,
                 enable_notification: bool = None,
                 **kwargs):
        super().__init__(**kwargs)

    def render_messages(self) -> DOM:
        def render_recursive(node: ComponentTreeNode):
            messages = []
            enable_notification = None

            if isinstance(node, WindowsGroup):
                enable_notification = node.props.enable_notification

            for child in node.rendered_children.values():
                if not isinstance(child, Window):
                    messages.extend(render_recursive(child))
                else:
                    message = child.render_message()
                    # override enable notification
                    if enable_notification is not None:
                        message.enable_notification = enable_notification

                    messages.append(message)

            return messages

        return render_recursive(self)
