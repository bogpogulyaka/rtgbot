import copy
import logging
import typing as tp
from collections.abc import Iterator


class PropsDict(object):
    __slots__ = ("_d", "_reactivity_manager")

    def __init__(self, dictionary: tp.Mapping[tp.Text, tp.Any], reactivity_manager):
        super().__setattr__("_d", dictionary)
        super().__setattr__("_reactivity_manager", reactivity_manager)
        # logging.info("create props")

    def __getitem__(self, key):
        value = self._d[key]
        self._reactivity_manager._record_value_read(key, True)
        return value

    def __setitem__(self, key, value):
        raise ValueError("Props are immutable")

    @property
    def _keys(self) -> Iterator:
        return self._d.keys()

    @property
    def _items(self) -> Iterator:
        return self._d.items()

    def _get(self, key: tp.Text, default: tp.Optional[tp.Any] = None) -> tp.Any:
        return self._d.get(key, default)

    def __len__(self):
        return len(self._d)

    def __iter__(self):
        return iter(self._d)

    def __contains__(self, k):
        return k in self._d

    def __getattr__(self, key):
        if key in self._d:
            self._reactivity_manager._record_value_read(key, True)
            return self._d[key]
        raise KeyError("%s not in props" % key)

    def __repr__(self):
        return "PropsDict(%s)" % repr(self._d)

    def __str__(self):
        return "PropsDict(%s)" % str(self._d)

    def __setattr__(self, key, value):
        raise ValueError("Props are immutable")
