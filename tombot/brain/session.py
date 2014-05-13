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
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#
#  The views and conclusions contained in the software and documentation
#  are those of the authors and should not be interpreted as representing
#  official policies, either expressedor implied, of konglx.
#
#  File        : user_manager.py
#  Author      : konglx
#  Email       : jayklx@gmail.com
#  Date        : 2014-03-08
#  Description : user and room management

from collections import deque
from hashlib import sha1
import os
import time
import datetime
import pickle
import base64

from tombot.common import log, config, utils


logger = log.logger


# from webpy
class Store(object):
    """Base class for session stores"""

    def __contains__(self, key):
        raise NotImplementedError

    def __getitem__(self, key):
        raise NotImplementedError

    def __setitem__(self, key, value):
        raise NotImplementedError

    def cleanup(self, timeout):
        """removes all the expired sessions"""
        raise NotImplementedError

    def encode(self, session_dict):
        """encodes session dict as a string"""
        pickled = pickle.dumps(session_dict)
        return base64.encodestring(pickled)

    def decode(self, session_data):
        """decodes the data to get back the session dict """
        pickled = base64.decodestring(session_data)
        return pickle.loads(pickled)


class DiskStore(Store):
    """
Store for saving a session on disk.

>>> import tempfile
>>> root = tempfile.mkdtemp()
>>> s = DiskStore(root)
>>> s['a'] = 'foo'
>>> s['a']
'foo'
>>> time.sleep(0.01)
>>> s.cleanup(0.01)
>>> s['a']
Traceback (most recent call last):
...
KeyError: 'a'
"""

    def __init__(self, root):
        # if the storage root doesn't exists, create it.
        if not os.path.exists(root):
            os.makedirs(os.path.abspath(root))
        self.root = root

    def _get_path(self, key):
        if os.path.sep in key:
            raise ValueError("Bad key: %s" % repr(key))
        return os.path.join(self.root, key)

    def __contains__(self, key):
        path = self._get_path(key)
        return os.path.exists(path)

    def __getitem__(self, key):
        path = self._get_path(key)
        if os.path.exists(path):
            pickled = open(path).read()
            return self.decode(pickled)
        else:
            #             raise KeyError(key)
            return None

    def __setitem__(self, key, value):
        path = self._get_path(key)
        pickled = self.encode(value)
        with open(path, 'w') as f:
            f.write(pickled)

    def __delitem__(self, key):
        path = self._get_path(key)
        if os.path.exists(path):
            os.remove(path)

    def cleanup(self, timeout):
        now = time.time()
        for f in os.listdir(self.root):
            path = self._get_path(f)
            atime = os.stat(path).st_atime
            if now - atime > timeout:
                os.remove(path)


class ShelfStore(object):
    """Store for saving session using `shelve` module.

import shelve
store = ShelfStore(shelve.open('session.shelf'))

XXX: is shelve thread-safe?
"""

    def __init__(self, shelf):
        self.shelf = shelf

    def __contains__(self, key):
        return key in self.shelf

    def __getitem__(self, key):
        atime, v = self.shelf[key]
        self[key] = v  # update atime
        return v

    def __setitem__(self, key, value):
        self.shelf[key] = time.time(), value

    def __delitem__(self, key):
        try:
            del self.shelf[key]
        except KeyError:
            pass

    def cleanup(self, timeout):
        now = time.time()
        for k in self.shelf.keys():
            atime, v = self.shelf[k]
            if now - atime > timeout:
                del self[k]


class DBStore(Store):
    """Store for saving a session in database
Needs a table with the following columns:

session_id CHAR(128) UNIQUE NOT NULL,
atime DATETIME NOT NULL default current_timestamp,
data TEXT
"""

    def __init__(self, db, table_name):
        self.db = db
        self.table = table_name

    def __contains__(self, key):
        data = self.db.select(self.table, where="session_id=$key", vars=locals())
        return bool(list(data))

    def __getitem__(self, key):
        now = datetime.datetime.now()
        try:
            s = self.db.select(self.table, where="session_id=$key", vars=locals())[0]
            self.db.update(self.table, where="session_id=$key", atime=now, vars=locals())
        except IndexError:
            raise KeyError
        else:
            return self.decode(s.data)

    def __setitem__(self, key, value):
        pickled = self.encode(value)
        now = datetime.datetime.now()
        if key in self:
            self.db.update(self.table, where="session_id=$key", data=pickled, vars=locals())
        else:
            self.db.insert(self.table, False, session_id=key, data=pickled)

    def __delitem__(self, key):
        self.db.delete(self.table, where="session_id=$key", vars=locals())

    def cleanup(self, timeout):
        timeout = datetime.timedelta(timeout / (24.0 * 60 * 60))  # timedelta takes numdays as arg
        last_allowed_time = datetime.datetime.now() - timeout
        self.db.delete(self.table, where="$last_allowed_time > atime", vars=locals())


class SessionExpired(Exception):
    pass


# store = DiskStore('{0}/run/sessions'.format(os.getenv('TOMBOT_HOME')))
import shelve

store = ShelfStore(shelve.open('{0}/run/session.db'.format(config.home)))


class Session(object):
    """
    Session implemention based on Room and User
    """
    __slots__ = [
        'store',
        '_killed',
        '_data',
        'session_id',
        '__getitem__',
        '__setitem__',
        '__delitem__'
    ]

    def __init__(self, rid, uid):
        self._data = utils.threadeddict()
        self._killed = False
        self.session_id = self.generate_session_id(rid, uid)
        # self._data = dict()
        self._data['session_id'] = self.generate_session_id(rid, uid)
        self._data['is_wait'] = False
        self._data['rid'] = rid
        self._data['uid'] = uid
        self._data['last'] = None
        self._data['history'] = deque(maxlen=10)

        self.store = store

        self.__getitem__ = self._data.__getitem__
        self.__setitem__ = self._data.__setitem__
        self.__delitem__ = self._data.__delitem__

        self._load()
        self._save()


    def __contains__(self, name):
        return name in self._data

    def __getattr__(self, name):
        return getattr(self._data, name)

    def __setattr__(self, name, value):
        if name in self.__slots__:
            object.__setattr__(self, name, value)
        else:
            setattr(self._data, name, value)

    def __delattr__(self, name):
        delattr(self._data, name)

    def _save(self):
        if not self.get('_killed'):
            self.store[self.session_id] = dict(self._data)

    def _load(self):
        d = self.store[self.session_id]
        self.update(d)

    @staticmethod
    def generate_session_id(rid, uid):
        session_id = sha1('{0}{1}'.format(rid, uid))
        session_id = session_id.hexdigest()
        return session_id

    def kill(self):
        del self.store[self.session_id]
        self._killed = True


plugin_store = DiskStore('{0}/run/sessions'.format(os.getenv('TOMBOT_HOME')))


#TODO 后续把插件的相关信息放到plugin session里
class PluginSession(Session):
    def __init__(self):
        self.store = plugin_store
        self._data = dict()
        self._secret_key = 'Dpxk,1*0fdwU&_8f71xFn<'
        self.psession_id = self._generate_session_id()
        self._data['psession_id'] = self.psession_id

    def _generate_session_id(self):
        rand = os.urandom(16)
        now = time.time()
        secret_key = self._secret_key
        psession_id = sha1('{0}{1}{2}'.format(rand, now, secret_key))
        psession_id = psession_id.hexdigest()
        return psession_id

    def __del__(self):
        del (self.store[self.psession_id])


class User(object):
    '''用户'''

    def __init__(self, user_id):
        self.uid = user_id
        self.permission = {"base": True}
        self.admin = False
        #历史记录最大10条
        self.history = deque(maxlen=10)

    def set_admin(self, boolean):
        if not type(boolean):
            raise TypeError
        self.admin = boolean


class Room(object):
    def __init__(self, room_id):
        self.rid = room_id
        self.rtype = None
        self.mode = config.default_mode
        self.users = {}
        self.session = None
        self.message = None


class RoomManager(object):
    def __init__(self):
        #{id: Room Object}
        self.rooms = {}

    def get_room(self, room_id):
        return self.rooms.get(room_id)

    def add_room(self, roomobj):
        self.rooms[roomobj.rid] = roomobj


class UserManager(object):
    '''用户管理器，储存所有用户信息'''
    users = {}

    def load_from_json(self, fp):
        '''从json载入用户属性'''
        '''
        {"id":123, {"permission", {"base":1, "script1": 1, "script2":0}}}
        '''
        pass

    def load_from_db(self):
        '''从redis载入用户属性'''
        pass
