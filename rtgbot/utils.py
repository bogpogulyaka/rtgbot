from enum import Enum

import rtgbot
import typing as tp


def unpack_kbd_buttons(kbd: rtgbot.components.base.KeyboardData) -> tp.List[rtgbot.etities.dom.ButtonElement]:
    buttons = []

    for kbd_row in kbd:
        buttons.extend(kbd_row)

    return buttons


def expand_component_tree(children):
    for child in children:
        if isinstance(child, tp.Callable):
            yield child
        elif isinstance(child, str):
            yield rtgbot.components.widgets.Const(child)
        elif isinstance(child, tp.Tuple):
            yield from expand_component_tree(child)
        else:
            yield rtgbot.components.widgets.BadComponent(type(child))


def expand_component_call_tree(children, display_exceptions):
    def expand(children):
        for child in children:
            if isinstance(child, rtgbot.base.ComponentTreeNode):
                yield child
            elif isinstance(child, str):
                yield rtgbot.components.widgets.Const(child)
            elif isinstance(child, tp.Tuple):
                yield from expand(child)
            elif isinstance(child, tp.Callable):
                try:
                    yield from expand((child(),))
                except Exception as e:
                    if display_exceptions:
                        yield rtgbot.components.widgets.ExceptionComponent(e)
            else:
                yield rtgbot.components.conditional.BadComponent(type(child))

    return expand(children)


class Symbols(str, Enum):
    EMPTY = '⠀'
    EMPTY2 = 'ㅤ'
    ZW = '&#8204;'
    ZW_HREF = '<a href="">&#8204;</a>'


def none_kw(**kwargs):
    return dict([(k, v) for k, v in kwargs.items() if v is not None])


def cond_kw(condition, **kwargs):
    if condition:
        return kwargs
    else:
        return dict()

