import functools
import inspect
import logging


def register_props(f):
    # logging.info("init props")

    varnames = f.__code__.co_varnames[1:]
    signature = inspect.signature(f).parameters
    defaults = {
        k: v.default for k, v in signature.items() if v.default is not inspect.Parameter.empty and k[0] != "_"
    }

    @functools.wraps(f)
    def func(self, *args, **kwargs):
        # logging.info("register props")
        name_to_val = defaults.copy()
        name_to_val.update(filter((lambda tup: (tup[0][0] != "_")), zip(varnames, args)))
        name_to_val.update(((k, v) for (k, v) in kwargs.items() if k[0] != "_"))
        self.register_props(name_to_val)
        f(self, *args, **kwargs)
        # if not isinstance(self, ComponentTreeNode):
        #     super().__init__(self, *kwargs)

    return func
