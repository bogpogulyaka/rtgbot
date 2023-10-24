from rtgbot.components.base import Component
from rtgbot.decorators import register_props
from rtgbot.utils import expand_component_call_tree


class Unsafe(Component):
    @register_props
    def __init__(self, display_exceptions=True, **kwargs):
        super().__init__(**kwargs)

    async def render(self):
        return tuple(expand_component_call_tree(self.props.children, self.props.display_exceptions))


class Show(Unsafe):
    @register_props
    def __init__(self, cond, **kwargs):
        super().__init__(**kwargs)

    async def render(self):
        checked_children = await super().render()

        if self.props.cond:
            children = list(map(lambda child: child if not isinstance(child, No) else Component(), checked_children))
        else:
            children = list(map(lambda child: child if isinstance(child, No) else Component(), checked_children))

        return *children,


class Yes(Component):
    def __init__(self, *children, **kwargs):
        super().__init__(**kwargs)
        self(*children)

    async def render(self):
        return Unsafe()(*self.props.children)


class No(Component):
    def __init__(self, *children, **kwargs):
        super().__init__(**kwargs)
        self(*children)

    async def render(self):
        return Unsafe()(*self.props.children)


class Switch(Component):
    @register_props
    def __init__(self, value, **kwargs):
        super().__init__(**kwargs)

    async def render(self):
        children = await super().render()

        for index, child in enumerate(children):
            if isinstance(child, Case) and child.props.value == self.props.value or \
               isinstance(child, Match) and child.props.cond:
                return Component(key=index)(child)


class Case(Unsafe):
    @register_props
    def __init__(self, value, **kwargs):
        super().__init__(**kwargs)


class Match(Unsafe):
    @register_props
    def __init__(self, cond, **kwargs):
        super().__init__(**kwargs)
