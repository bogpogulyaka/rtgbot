import math

from rtgbot.components.base import Component
from rtgbot.decorators import register_props
from rtgbot.etities.dom import ButtonElement
from rtgbot.utils import unpack_kbd_buttons, Symbols


class Group(Component):
    @register_props
    def __init__(self, width=None, max_width=None, fill_tail=False, fill_evenly=False, style=None, **kwargs):
        if not style:
            style = {}
        style['kbd_width'] = width
        style['kbd_max_width'] = max_width
        style['fill_tail'] = fill_tail
        style['fill_evenly'] = fill_evenly

        super().__init__(style=style, **kwargs)

    def render_kbd(self):
        rendered_kbd = super().render_kbd()

        width = self.props.width
        max_width = self.props.max_width

        if width is not None:
            buttons = unpack_kbd_buttons(rendered_kbd)
            bnt_cnt = len(buttons)

            width = min(width, 8)
            if max_width is not None:
                width = min(width, max_width)

            if self.props.fill_evenly:
                width = (bnt_cnt - 1) // ((bnt_cnt - 1) // 8 + 1) + 1

            kbd = [buttons[i:i + width] for i in range(0, len(buttons), width)]

            if self.props.fill_tail and bnt_cnt > width:
                row = kbd[-1]
                row.extend([ButtonElement(tree_node=self, text=Symbols.EMPTY) for _ in range(width - len(row))])

            return kbd

        elif max_width is not None:
            max_width = min(max_width, 8)
            kbd = []

            for row in rendered_kbd:
                kbd.extend([row[i:i + max_width] for i in range(0, len(row), max_width)])

            return kbd

        return rendered_kbd


class Row(Group):
    @register_props
    def __init__(self, **kwargs):
        super().__init__(width=9999, **kwargs)


class Column(Group):
    @register_props
    def __init__(self, **kwargs):
        super().__init__(width=1, **kwargs)
