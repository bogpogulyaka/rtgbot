from __future__ import annotations

import hashlib
import typing as tp
from dataclasses import dataclass, field
from enum import Enum, auto

import aiogram
from aiogram import types
from aiogram.enums import ContentType, InputMediaType

import rtgbot


@dataclass
class RenderContext:
    bot: aiogram.Bot
    user_id: int
    navigator: tp.Any
    event_manager: tp.Any
    render_cycle_id: int = 0
    is_banned: bool = False


@dataclass
class DOMElement:
    tree_node: tp.Any
    render_cycle_id: int = field(init=False)

    def __post_init__(self):
        self.render_cycle_id = self.tree_node.render_cycle_id


@dataclass
class ButtonElement(DOMElement):
    text: str = ""
    url: str = ""
    callback: tp.Callable = None
    button_id: str = field(init=False)

    def __post_init__(self):
        super().__post_init__()
        self.button_id = hashlib.blake2b(self.tree_node.rendered_chained_key.encode(), digest_size=4).hexdigest()

    def __eq__(self, other):
        return \
            self.text == other.text and \
            self.url == other.url and \
            self.tree_node.rendered_chained_key == other.tree_node.rendered_chained_key


KeyboardData = tp.List[tp.List[ButtonElement]]


@dataclass
class InputElement(DOMElement):
    content_types: tp.Union[tp.Sequence[str], str] = ContentType.ANY
    callback: tp.Callable = None


@dataclass
class MediaElement(DOMElement):
    type: InputMediaType
    url: str = None
    path: str = None

    def __eq__(self, other):
        img1 = self.url and self.url or self.path
        img2 = other.url and other.url or other.path
        return img1 == img2


@dataclass
class MessageElement(DOMElement):
    media: tp.List[MediaElement]
    text: str
    keyboard: KeyboardData
    inputs: tp.List[InputElement]

    parse_mode: tp.Optional[str]
    disable_web_page_preview: bool
    enable_notification: bool

    key: str = ''

    def __post_init__(self):
        self.key = self.tree_node.rendered_chained_key

    def compare_media(self, other: MessageElement):
        if len(self.media) != len(other.media):
            return False

        for i in range(0, len(self.media)):
            if self.media[i] != other.media[i]:
                return False

        return True

    def compare_text(self, other: MessageElement):
        return self.text == other.text

    def compare_kbd(self, other: MessageElement):
        kbd1 = rtgbot.utils.unpack_kbd_buttons(self.keyboard)
        kbd2 = rtgbot.utils.unpack_kbd_buttons(other.keyboard)

        if len(kbd1) != len(kbd2):
            return False

        for i in range(0, len(kbd1)):
            if kbd1[i] != kbd2[i]:
                return False

        return True

    def edit_cost(self, other: MessageElement):
        m = not self.compare_media(other) and len(other.media) or 0
        t = not self.compare_text(other)
        k = not self.compare_kbd(other)

        return m * 10 + t * 2 + k

    def can_edit(self, other: MessageElement):
        return (len(self.media) == 0) == (len(other.media) == 0)

    @property
    def send_cost(self):
        m = len(self.media)
        return m * 10 + 2 + 1


DOM = tp.List[MessageElement]


@dataclass
class DOMMessageUpdate:
    class Action(Enum):
        keep = auto()
        update = auto()
        delete = auto()
        send = auto()

    action: Action
    old_message: tp.Optional[MessageElement] = None
    new_message: tp.Optional[MessageElement] = None


DOMUpdate = tp.List[DOMMessageUpdate]
