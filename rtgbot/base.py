import logging
import types
import typing as tp
from abc import ABC
from dataclasses import dataclass, field

import rtgbot
from rtgbot.etities.context import RenderContext
from rtgbot.props_dict import PropsDict
from rtgbot.decorators import register_props
from rtgbot.reactivity_manager import ReactivityManager

ComponentTreeNodeChild = tp.Union['ComponentTreeNode', str]
ComponentTreeNodeChildren = ComponentTreeNodeChild | tp.Tuple[ComponentTreeNodeChild, ...]


@dataclass
class RenderData:
    parent: tp.Optional['ComponentTreeNode'] = None
    children: tp.Dict[tp.Any, 'ComponentTreeNode'] = field(default_factory=dict)
    children_visible: tp.Dict[tp.Any, 'ComponentTreeNode'] = field(default_factory=dict)
    key = None
    chained_key: tp.Optional[str] = None
    render_cycle_id: int = 0

    def set_key(self, value):
        self.key = value
        self.chained_key = None

    def get_chained_key(self):
        if self.parent is None:
            return None

        if self.chained_key:
            return self.chained_key

        if self.parent:
            key = str(self.key)
            parent_key = self.parent.rendered_chained_key

            if parent_key:
                self.chained_key = parent_key + '.' + key
            else:
                self.chained_key = key

        return self.chained_key


class ComponentTreeNode(ABC):
    _attr_blacklist = {'register_props', 'props', 'context', 'rct',
                       'invalidate', 'set_state', 'emit',
                       'setup', 'before_mount', 'mounted', 'before_mount', 'render',
                       'activated', 'deactivated', 'updated', 'before_unmount', 'unmounted', 'on_event'}

    @register_props
    # id: str = None,
    def __init__(self, key=None, when=True, visible=True, style: dict = None):
        self._render_data = RenderData()
        self._reactivity_manager = ReactivityManager(self)
        self._context: tp.Optional[RenderContext] = None

        self._is_dirty = False
        self._can_push_notifications = False

        try:
            states = self.States
            state = list(states.__members__.values())[0]
            object.__setattr__(self, 'state', state)
        except Exception:
            object.__setattr__(self, 'state', None)

    def register_props(self, props: tp.Mapping[tp.Text, tp.Any]):
        if not hasattr(self, "_props"):
            self._props = {"children": []}
        self._props.update(props)

    @property
    def props(self) -> PropsDict:
        return PropsDict(self._props, self._reactivity_manager)

    @property
    def context(self):
        return self._context

    @property
    def rct(self):
        return self._reactivity_manager

    @property
    def render_cycle_id(self):
        return self._render_data.render_cycle_id

    @property
    def rendered_children(self):
        return self._render_data.children_visible

    @property
    def rendered_children_all(self):
        return self._render_data.children

    @property
    def rendered_key(self):
        return self._render_data.key

    @property
    def rendered_chained_key(self):
        return self._render_data.get_chained_key()

    @property
    def is_visible(self):
        parent = self._render_data.parent
        return self.props.visible and (parent is None or parent.is_visible)

    def __call__(self, *args):
        self._props["children"] = list(rtgbot.utils.expand_component_tree(args))
        return self

    def __getattribute__(self, key):
        value = super().__getattribute__(key)

        if key[0] != '_' and key not in self._attr_blacklist:
            r_manager = super().__getattribute__('_reactivity_manager')
            if r_manager:
                r_manager._record_value_read(key, False)

        return value

    def __setattr__(self, key, value):
        if key[0] != '_':
            r_manager = super().__getattribute__('_reactivity_manager')
            if r_manager:
                r_manager._set_value(key, value, False)
            else:
                super().__setattr__(key, value)
            if self.context and self._can_push_notifications:
                self.context.event_manager.push_node_modification(self)
        else:
            super().__setattr__(key, value)

    def invalidate(self):
        self._is_dirty = True
        if self._can_push_notifications:
            self.context.event_manager.push_node_modification(self)

    def set_state(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self, k):
                self.__setattr__(k, v)

    def emit(self, name: str, **kwargs):
        self.context.event_manager.push_custom_event(sender=self, name=name, data=kwargs)

    async def setup(self):
        pass

    async def before_mount(self):
        pass

    async def mounted(self):
        pass

    async def before_update(self):
        pass

    async def render(self) -> ComponentTreeNodeChildren:
        return *self.props.children,

    async def activated(self):
        pass

    async def deactivated(self):
        pass

    async def updated(self):
        pass

    async def before_unmount(self):
        pass

    async def unmounted(self):
        pass

    async def on_event(self, event):
        pass

    # async def watch_effect(self):
    #     pass
