import typing as tp
from enum import Enum, auto

import rtgbot


class NavigationMode(Enum):
    default = auto()


class Navigator:
    def __init__(self, navigation_stack, start_screen):
        self._navigation_stack = navigation_stack
        self._stack = [(start_screen, [start_screen.state])]

    @property
    def stack(self):
        return self._stack

    def navigate(self,
                 to: tp.Callable[[], rtgbot.components.base.Window | rtgbot.components.base.WindowsGroup] = None, state=None,
                 mode=NavigationMode.default, replace=False):
        if to is None and state is None:
            return

        push_new = to is not None
        if push_new:
            screen = to()
        else:
            screen = self._stack[-1][0]

        if state is not None:
            screen.state = state
            # object.__setattr__(screen, 'state', state)
        else:
            state = screen.state

        if push_new:
            if replace:
                self._stack.pop()
            self._stack.append((screen, [state]))
            self._navigation_stack.invalidate()
        else:
            if replace:
                self._stack[-1][1].pop()
            self._stack[-1][1].append(state)

    def back(self, to: str = None, state=None):
        if len(self._stack) <= 1:
            return False

        if to is None and state is None:
            screen, screen_states = self._stack[-1]
            if len(screen_states) > 1:
                screen_states.pop()
                screen.state = screen_states[-1]
            elif len(self._stack) > 1:
                self._stack.pop()
                self._navigation_stack.invalidate()

        stack_changed = False

        if to:
            is_route_found = False

            for stack_index in range(len(self._stack) - 1, -1, -1):
                screen, _ = self._stack[stack_index]

                stack_changed = True

                if self._find_route(screen) == to:
                    is_route_found = True
                    self._stack = self._stack[:stack_index + 1]
                    break

            if not is_route_found:
                return False

        if stack_changed:
            self._navigation_stack.invalidate()

        if state:
            is_state_found = False
            screen, screen_states = self._stack[-1]

            for state_index in range(len(screen_states) - 1, -1, -1):
                if screen_states[state_index] == state:
                    is_state_found = True
                    screen.state = state
                    self._stack[-1] = screen, screen_states[:state_index + 1]
                    break

            if not is_state_found:
                return False

        return True

    def _find_route(self, screen):
        if isinstance(screen, rtgbot.components.base.Window | rtgbot.components.base.WindowsGroup):
            route = screen.props.route
            if route:
                return route

        for child_node in screen.rendered_children.values():
            route = self._find_route(child_node)
            if route:
                return route

    def reset(self):
        while self.back():
            pass
