# coding: utf-8

from tombot.brain import holder
from tombot.brain.bot import TomBot

from tombot.common.log import logger


def run():
    holder.bot = TomBot()
    holder.bot.activate_non_started_plugins()
    logger.info("Bot's commands: {}".format(holder.bot.get_commands()))
    holder.bot.serve_forever()


if __name__ == '__main__':
    run()
