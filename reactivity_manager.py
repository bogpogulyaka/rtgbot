from __future__ import annotations

import asyncio
import logging
import types
import typing as tp
from copy import copy
from dataclasses import dataclass, field


class ReactivityManager:
    @dataclass
    class WatchedExpression:
        expr: tp.Callable[[], tp.Any]
        deps: tp.List[str]
        value: tp.Any
        target: str = None
        callback: tp.Callable[[tp.Any, tp.Any], None | tp.Coroutine] = None

        def __hash__(self):
            return id(self)

    @dataclass
    class ComponentValue:
        curr: tp.Any
        prev: tp.Any = None
        is_new = True
        watched_expr: tp.Optional[ReactivityManager.WatchedExpression] = None
        dep_watchers: tp.Set[ReactivityManager.WatchedExpression] = field(default_factory=set)

    def __init__(self, component):
        self._component = component

        self._values: tp.Dict[str, ReactivityManager.ComponentValue] = {}

        self._is_recording_enabled = False
        self._recorded_reads = []

    def computed(self, expr: tp.Callable[[], tp.Any]):
        try:
            watched_expr = self._evaluate_expression(expr)
            return tp.cast(ComputedValue, watched_expr)
        except Exception:
            logging.exception("Exception occurred while creating computed value:")
            return None

    def watch(self, expr: tp.Callable[[], tp.Any], callback: tp.Callable[[tp.Any, tp.Any], tp.Coroutine], immediate=True):
        try:
            watched_expr = self._evaluate_expression(expr)
            watched_expr.callback = callback

            if immediate:
                self._call_watcher_callback(callback, watched_expr.value, None)
        except Exception:
            logging.exception("Exception occurred while creating watcher:")

    def _evaluate_expression(self, expr):
        self._is_recording_enabled = True
        self._recorded_reads = []

        exception = None
        value = None
        try:
            value = expr()
        except Exception as e:
            exception = e

        self._is_recording_enabled = False

        if exception is not None:
            raise exception

        watched_expr = self.WatchedExpression(
            expr=expr,
            value=value,
            deps=list(set(self._recorded_reads))
        )

        # register new watch
        self._register_watcher_deps(watched_expr)

        return watched_expr

    def _call_watcher_callback(self, callback, new_value, prev_value):
        if asyncio.iscoroutinefunction(callback):
            asyncio.create_task(callback(new_value, prev_value))
        else:
            try:
                callback(new_value, prev_value)
            except Exception:
                logging.exception("Exception in watcher callback:")

    def _set_value(self, key, value, is_property):
        if is_property:
            key = '$' + key

        watched_expr = None

        if isinstance(value, ComputedValue):
            watched_expr = value
            watched_expr.target = key
            value = watched_expr.value

        if not is_property:
            object.__setattr__(self._component, key, value)

        value_changed = True

        # set state value
        if key in self._values:
            component_val = self._values[key]
            if component_val.curr == value:
                value_changed = False
            component_val.curr = value

            # unregister current watch
            if component_val.watched_expr:
                self._unregister_watcher_deps(component_val.watched_expr)

            # set new watch
            component_val.watched_expr = watched_expr
        else:
            component_val = self.ComponentValue(curr=value, watched_expr=watched_expr)
            self._values[key] = component_val

        if value_changed:
            if is_property and len(component_val.dep_watchers) > 0:
                pass

            # propagate update
            for dep_watcher in copy(component_val.dep_watchers):
                try:
                    new_watched_expr = self._evaluate_expression(dep_watcher.expr)
                    new_watched_expr.target = dep_watcher.target
                    new_watched_expr.callback = dep_watcher.callback

                    if dep_watcher.target:
                        setattr(self._component, dep_watcher.target, new_watched_expr)
                    else:
                        self._unregister_watcher_deps(dep_watcher)
                        self._call_watcher_callback(dep_watcher.callback, new_watched_expr.value, dep_watcher.value)
                except Exception:
                    logging.exception("Exception occurred while calling watcher expression:")

    def _record_value_read(self, key, is_property):
        if self._is_recording_enabled:
            if is_property:
                key = '$' + key
            self._recorded_reads.append(key)

    def _register_watcher_deps(self, watched_expr):
        for key in watched_expr.deps:
            try:
                self._values[key].dep_watchers.add(watched_expr)
            except KeyError:
                pass

    def _unregister_watcher_deps(self, watched_expr):
        for key in watched_expr.deps:
            try:
                self._values[key].dep_watchers.remove(watched_expr)
            except KeyError:
                pass

    def _reset_state_history(self):
        has_changed = False

        for value in self._values.values():
            if value.curr != value.prev or value.is_new:
                value.prev = value.curr
                value.is_new = False
                has_changed = True

        return has_changed


ComputedValue = ReactivityManager.WatchedExpression
