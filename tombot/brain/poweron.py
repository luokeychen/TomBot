# coding: utf-8

from tombot.brain import holder
from tombot.brain.bot import TomBot
from tombot.common.log import logger
from tombot.rest.api import threaded_api_server


def run():
    holder.bot = TomBot()
    holder.bot.activate_non_started_plugins()
    threaded_api_server()
    holder.bot.serve_forever()


if __name__ == '__main__':
    run()
