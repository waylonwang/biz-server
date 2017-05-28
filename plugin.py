import importlib
import os
import sys

from env import get_plugin_dir


class PluginsRegistry:
    """
    Represent a map of plugins and functions.
    """

    def __init__(self, init_func = None):
        self.init_func = init_func
        self.model_map = {}
        self.view_map = {}

    def register_model(self, order):
        def decorator(cls):
            self.model_map[order] = cls
            return cls

        return decorator

    def register_view(self):
        def decorator(cls):
            self.view_map[cls.__name__] = cls
            return cls

        return decorator


class PluginsHub:
    """
    Represent series of command registries,
    which means it's used as a collection of different registries
    and allows same command names.
    """

    def __init__(self):
        self.registry_map = {}

    def add_registry(self, registry_name, registry):
        """
        Add a registry to the hub, running the init function of the registry.

        :param registry_name: registry name
        :param registry: registry object
        """
        if registry.init_func:
            registry.init_func()
        self.registry_map[registry_name] = registry


hub = PluginsHub()


def _init_mod(mod, app):
    mod_name = mod.__name__.split('.')[1]
    try:
        if hasattr(mod, "init"):
            mod.init(app)
    except:
        print('Failed to init plugin module "' + mod_name + '.py".', file = sys.stderr)


def _add_registry_mod_cb(mod):
    mod_name = mod.__name__.split('.')[1]
    try:
        if hasattr(mod, "__registry__"):
            hub.add_registry(mod_name, mod.__registry__)
    except AttributeError:
        print('Failed to load plugin module "' + mod_name + '.py".', file = sys.stderr)


def load_plugins(plugin_dir_name, app = None):
    plugin_dir = get_plugin_dir(plugin_dir_name)
    plugin_files = filter(
        lambda filename: filename.endswith('.py') and not filename.startswith('_'),
        os.listdir(plugin_dir)
    )
    plugins = [os.path.splitext(file)[0] for file in plugin_files]
    for mod_name in plugins:
        mod = importlib.import_module(plugin_dir_name + '.' + mod_name)
        _init_mod(mod, app)
        _add_registry_mod_cb(mod)