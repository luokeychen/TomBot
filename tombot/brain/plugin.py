#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#  Copyright (C) 2014 konglx
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met:
#  1. Redistributions of source code must retain the above copyright
#  notice, this list of conditions and the following disclaimer.
#  2. Redistributions in binary form must reproduce the above copyright
#  notice, this list of conditions and the following disclaimer in the
#  documentation and/or other materials provided with the distribution.
#
#  THIS SOFTWARE IS PROVIDED BY konglx ''AS IS'' AND ANY
#  EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#  WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#  DISCLAIMED. IN NO EVENT SHALL konglx BE LIABLE FOR ANY
#  DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#  (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#   LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#  ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#
#  The views and conclusions contained in the software and documentation
#  are those of the authors and should not be interpreted as representing
#  official policies, either expressedor implied, of konglx.
#
#  File        : plugin.py
#  Author      : konglx
#  Email       : jayklx@gmail.com
#  Date        : 2014-03-29
#  Description : manage plugins
# TODO make ansible and builtin and user plugins separately

import sys
import os
from itertools import chain

from yapsy.PluginManager import PluginManager

from tombot.brain import holder
from tombot.common import log, config
from tombot.brain.engine import Engine, AnsibleEngine, BuiltinEngine


logger = log.logger

BUILTIN = config.home + os.sep + 'builtins'


def get_builtins(extra):
    # adds the extra plugin dir from the setup for developers convenience
    if extra:
        if isinstance(extra, list):
            return [BUILTIN] + extra
        return [BUILTIN, extra]
    else:
        return [BUILTIN]


def init_plugin_manager():
    global tom_plugin_manager
    from engine import BuiltinEngine, AnsibleEngine, Engine

    if not holder.plugin_manager:
        tom_plugin_manager = PluginManager()
        tom_plugin_manager.setPluginPlaces(config.plugin_dirs)
        tom_plugin_manager.setPluginInfoExtension('plug')
        # 3 types of plugins, Built-in for plugin come with Tom,
        # Ansible for ansible simplerunner or playbook running on tom
        # User for user-defined plugins
        tom_plugin_manager.setCategoriesFilter({
            'Built-in': BuiltinEngine,
            'Ansible': AnsibleEngine,
            'User': Engine
        })
        tom_plugin_manager.collectPlugins()
        holder.plugin_manager = tom_plugin_manager
    else:
        tom_plugin_manager = holder.plugin_manager


class TomPluginManager(PluginManager):
    def __init__(self):
        super(TomPluginManager, self).__init__()
        self.setPluginPlaces(config.plugin_dirs)
        self.setPluginInfoExtension('plug')
        self.setCategoriesFilter({
            'Built-in': BuiltinEngine,
            'Ansible': AnsibleEngine,
            'User': Engine
        })
        self.collectPlugins()


init_plugin_manager()


def get_plugin_by_name(name):
    pta_item = tom_plugin_manager.getPluginByName(name, 'bots')
    if pta_item is None:
        return None
    return pta_item


def get_plugin_obj_by_name(name):
    plugin = get_plugin_by_name(name)
    return None if plugin is None else plugin.plugin_object


def populate_doc(plugin):
    plugin_type = type(plugin.plugin_object)
    plugin_type.__errdoc__ = plugin_type.__doc__ if plugin_type.__doc__ else plugin.description


def activate_plugin_by_name(name):
    pta_item = tom_plugin_manager.getPluginByName(name, 'User')
    # pta_item = tom_plugin_manager.getPluginByName(name, 'Built-in')
    # pta_item = tom_plugin_manager.getPluginByName(name, 'Ansible')
    if pta_item is None:
        logger.warning('Could not activate %s' % name)
        return None
    obj = pta_item.plugin_object

    populate_doc(pta_item)
    try:
        return tom_plugin_manager.activatePluginByName(name, "User")
    except Exception as _:
        pta_item.activated = False  # Yapsy doesn't revert this in case of error
        logger.error("Plugin %s failed at activation stage, deactivating it..." % name)
        tom_plugin_manager.deactivatePluginByName(name, "User")
        raise


def deactivate_plugin_by_name(name):
    pta_item = tom_plugin_manager.getPluginByName(name, 'User')
    try:
        return tom_plugin_manager.deactivatePluginByName(name, "User")
    except Exception as _:
        raise


def reload_plugin_by_name(name):
    """
    Completely reload the given plugin, including reloading of the module's code
    """
    if name in get_all_active_plugin_names():
        deactivate_plugin_by_name(name)

    plugin = get_plugin_by_name(name)
    logger.critical(dir(plugin))
    module = __import__(plugin.path.split(os.sep)[-1])
    reload(module)

    class_name = type(plugin.plugin_object).__name__
    new_class = getattr(module, class_name)
    plugin.plugin_object.__class__ = new_class


def update_plugin_places(list):
    BOT_EXTRA_PLUGIN_DIR = config.plugin_dirs
    builtins = get_builtins(BOT_EXTRA_PLUGIN_DIR)
    for entry in chain(builtins, list):
        if entry not in sys.path:
            sys.path.append(entry)  # so the plugins can relatively import their submodules

    tom_plugin_manager.setPluginPlaces(chain(builtins, list))
    all_candidates = []

    def add_candidate(candidate):
        all_candidates.append(candidate)

    tom_plugin_manager.locatePlugins()
    #noinspection PyBroadException
    try:
        tom_plugin_manager.loadPlugins(add_candidate)
    except Exception as _:
        logger.exception("Error while loading plugins")

    # FIXME temporary keep it from errbot
    errors = None

    return all_candidates, errors


def get_all_plugins():
    logger.debug("All plugins: %s" % tom_plugin_manager.getAllPlugins())
    return tom_plugin_manager.getAllPlugins()


def get_all_active_plugin_objects():
    return [plug.plugin_object for plug in get_all_plugins() if hasattr(plug, 'is_activated') and plug.is_activated]


def get_all_active_plugin_names():
    return [p.name for p in get_all_plugins() if hasattr(p, 'is_activated') and p.is_activated]


def get_all_plugin_names():
    return [p.name for p in get_all_plugins()]


def deactivate_all_plugins():
    for name in get_all_active_plugin_names():
        tom_plugin_manager.deactivatePluginByName(name, "bots")


def global_restart():
    python = sys.executable
    os.execl(python, python, *sys.argv)


# class PluginManager(Thread):
#     '''插件管理器'''
#     def __init__(self, identity=None, pushsock=None):
#         super(PluginManager, self).__init__()
#         self.backend = None
#         self.pushsock = pushsock
#         self.identity = identity
#         self.plugins = {}

#         self.daemon = False

#     def load_scripts(self, type_):
#         '''载入插件 '''
#         plugins = None
#         if type_ == 'plugin':
#             plugins = config.plugins
#         if type_ == 'ansible':
#             plugins = config.runners

#         if plugins is None:
#             return

#         for plugin in plugins:
#             self.run_script(plugin)

#     def run_script(self, plugin):
#         '''载入运行插件，同时将插件注册到PluginManager'''
#         sys.path.append('plugins')
#         sys.path.append('{0}/tombot/ansible/'.format(config.home))

#         try:
#             m = import_module(plugin)
#         except ImportError as e:
#             logger.error('{0}插件载入失败，错误信息：{1}'.format(plugin, e))
#             return 1

#         for item in dir(m):
#             attr = getattr(m, item)
#             载入所有插件类
#             if isclass(attr) and hasattr(attr, '__plugin__'):
#                 _instance = attr()
#                 self.plugins[plugin] = Plugin(_instance, m)
#                 self.plugins[plugin].plugin_manager = self
#                 logger.info('实例化脚本{0}的{1}类...'.format(plugin, attr.__name__))
#         logger.info('成功载入的插件:{0}'.format(self.plugins.keys()))

#     def recv_callback(self, msg):
#         '''收到消息的回调'''
#         logger.debug('PLUGINMANAGER收到消息:{0}'.format(msg))
#         identity = msg[0]
#         msg_body = json.loads(msg[1])
#         id_ = msg_body.get('id')
#         content = msg_body.get('content')
#         type_ = msg_body.get('type')
#         user = msg_body.get('user')

#         session = Session(id_, user)
#         logger.debug('plugin session:{0}'.format(session._data))

#         msg = Message((identity, content, id_, type_, user),
#                       self.pushsock
#                       )
#         self.parse_command(msg, session)

#     def parse_command(self, msg, session=None):
#         '''找到插件里的响应函数，并进行处理'''
#         match_result = {}
#         for name, plugin in self.plugins.iteritems():
#             match_result[name] = plugin.respond(msg, session)
#             if match_result[name] == '__I_AM_WAITING__':
#                 break

#         if match_result is None:
#             logger.info('没有插件或结果错误')
#             return

#         若找不到匹配，则返回错误
#         if not [res for res in match_result.values() if res is not None]:
#             msg.error('未找到匹配命令或格式有误')

#         logger.info('匹配结果：{0}'.format(match_result))

#     def run(self):
#         context = zmq.Context(1)
#         backsock = context.socket(zmq.SUB)
#         backsock.setsockopt(zmq.SUBSCRIBE, '')
#         backsock.connect('ipc://{0}/backend_{1}.ipc'.format(config.ipc_path,
#                                                             self.identity))

#         注册tornado IOLoop回调
#         stream = zmqstream.ZMQStream(backsock)
#         stream.on_recv(self.recv_callback)


# class Plugin(object):
#     '''将respond中的响应对象转换成Plugin对象'''
#     def __init__(self, instance, module):
#         self.instance = instance
#         self.module = module
#         self.plugin_manager = None
#         self.name = module.__name__
#         self.respond_map = module.respond.respond_map
#         self.session = None
#         self._wrap_method()

#     def _wrap_method(self):
#         '''用修饰器处理respond_map中的方法时，会丢失属性，使其变成function
#         这里要重新绑定到实例，使其成为实例的方法
#         '''
#         for pattern, func in self.respond_map.iteritems():
#             获取注册的function
#             func = self.module.respond.get_respond(pattern)
#             动态绑定function为instance的method
#             func, queue = self.respond_map[pattern]
#             self.respond_map[pattern] = types.MethodType(func, self.instance), queue

#     def respond(self, msg, session):
#         pool = ThreadPool(20)

#         if session['iswait']:
#             queue = self._get_queue(session['last'])
#             queue.put(msg)
#             return '__I_AM_WAITING__'

#         for pattern, method in self.respond_map.iteritems():
#             matches = re.match(pattern, msg.content)
#             if matches:
#                 logger.debug('匹配分组:{0}'.format(matches.groups()))
#                 func, queue = self.respond_map[pattern]
#                 pool.add_task(func, msg, matches)
#         return matches

#     def _get_queue(self, wait_pattern):
#         for plugin in self.plugin_manager.plugins.values():
#             for pattern, (func, queue) in plugin.respond_map.iteritems():
#                 if pattern == wait_pattern:
#                     return queue


