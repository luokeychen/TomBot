import ansible.runner
import ansible.inventory
import logging
import os
import re

from engine import Respond, plugin
respond = Respond()
logger = logging.getLogger(__name__)


@plugin
class CheskOS(object):
