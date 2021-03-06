from gettext import gettext as _
from pprint import pformat
import copy
import logging

from pulp.plugins.loader import exceptions as loader_exceptions


_logger = logging.getLogger(__name__)


class PluginManager(object):
    """
    Class to manage heterogeneous types of plugins including their class,
    configuration, and supported types associations.
    """

    def __init__(self):
        self.distributors = _PluginMap()
        self.group_distributors = _PluginMap()
        self.group_importers = _PluginMap()
        self.importers = _PluginMap()
        self.profilers = _PluginMap()
        self.catalogers = _PluginMap()


class _PluginMap(object):
    """
    Convenience class for managing plugins of a homogeneous type.
    @ivar configs: dict of associated configurations
    @ivar plugins: dict of associated classes
    @ivar types: dict of supported types the plugins operate on
    """

    def __init__(self):
        self.configs = {}
        self.plugins = {}
        self.types = {}

    def add_plugin(self, id, cls, cfg, types=()):
        """
        @type id: str
        @type cls: type
        @type cfg: dict
        @type types: list or tuple
        """
        if not cfg.get('enabled', True):
            _logger.info(_('Skipping plugin %(p)s: not enabled') % {'p': id})
            return
        if self.has_plugin(id):
            msg = _('Plugin with same id already exists: %(n)s')
            raise loader_exceptions.ConflictingPluginName(msg % {'n': id})
        self.plugins[id] = cls
        self.configs[id] = cfg
        for type_ in types:
            plugin_ids = self.types.setdefault(type_, [])
            plugin_ids.append(id)
        _logger.info(_('Loaded plugin %(p)s for types: %(t)s') %
                     {'p': id, 't': ','.join(types)})
        _logger.debug('class: %s; config: %s' % (cls.__name__, pformat(cfg)))

    def get_plugin_by_id(self, id):
        """
        @type id: str
        @rtype: tuple (type, dict)
        @raises L{PluginNotFound}
        """
        if not self.has_plugin(id):
            raise loader_exceptions.PluginNotFound(_('No plugin found: %(n)s') % {'n': id})
        # return a deepcopy of the config to avoid persisting external changes
        return self.plugins[id], copy.deepcopy(self.configs[id])

    def get_plugins_by_type(self, type_):
        """
        @type type_: str
        @rtype: list of tuples (cls, config)
        @raise: L{exceptions.PluginNotFound}
        """
        ids = self.get_plugin_ids_by_type(type_)
        return [(self.plugins[id], self.configs[id]) for id in ids]

    def get_plugin_ids_by_type(self, type_):
        """
        @type type_: str
        @rtype: tuple (str, ...)
        @raises L{PluginNotFound}
        """
        plugins = self.types.get(type_, [])
        if not plugins:
            raise loader_exceptions.PluginNotFound(_('No plugin found for: %(t)s') % {'t': type_})
        return tuple(plugins)

    def get_loaded_plugins(self):
        """
        @rtype: dict {str: dict, ...}
        """
        return dict((id, cls.metadata()) for id, cls in self.plugins.items())

    def has_plugin(self, id):
        """
        @type id: str
        @rtype: bool
        """
        return id in self.plugins

    def remove_plugin(self, id):
        """
        @type id: str
        """
        if not self.has_plugin(id):
            return
        self.plugins.pop(id)
        self.configs.pop(id)
        for type_, ids in self.types.items():
            if id not in ids:
                continue
            ids.remove(id)
