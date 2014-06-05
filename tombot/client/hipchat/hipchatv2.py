#! /usr/bin/env python
# coding: utf-8
# LICENSE:
# Date:
# Author: konglx
# File:
# Description:

__author__ = 'Konglx'

from hypchat import HypChat
from tombot.common.log import logger

TOKEN = 'DZttvKCWeU4GpXxoqwJc4IG8bH636MjaCmLNZqc8'

hc = HypChat(TOKEN)

logger.debug('Hipchat rooms: {0}'.format(hc.rooms()))
logger.debug('Hipchat users: {0}'.format(hc.users()))
