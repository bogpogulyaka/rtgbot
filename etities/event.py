from __future__ import annotations

import typing as tp
from dataclasses import dataclass, field

from aiogram.types import Message

import rtgbot


@dataclass
class Event:
    sender: rtgbot.base.ComponentTreeNode
    dom_element: rtgbot.etities.dom.DOMElement = None
    name: str = ""
    _should_propagate = True

    def stop_propagation(self):
        self._should_propagate = False

    @property
    def should_propagate(self):
        return self._should_propagate

    def __str__(self):
        return self.name


@dataclass
class ButtonClickEvent(Event):
    def __post_init__(self):
        self.name = "click"

    def __str__(self):
        return f"click {self.dom_element.text}"


@dataclass
class MessageInputEvent(Event):
    tg_message: Message = None

    def __post_init__(self):
        self.name = "input"


@dataclass
class CustomEvent(Event):
    data: tp.Dict = field(default_factory=dict)
