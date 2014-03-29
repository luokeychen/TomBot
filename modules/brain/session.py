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

import config


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
