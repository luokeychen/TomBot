# coding: utf-8
 
import urllib2
import urllib
import re
import threading
import time

from xml.sax.saxutils import unescape
import os
import logging
import random
from engine import Engine
from engine import respond_handler
import utils

from BeautifulSoup import BeautifulSoup          # For processing HTML

_path = os.path.abspath(os.path.dirname(__file__))

qiushi = _path + "/qiushi.txt"

class Qiubai(Engine):
    '''Tom make me laugh\t 发送一则笑话（来自糗百）'''

    def __init__(self):
        self.jokes = []

    @respond_handler('make me laugh$')
    def respond(self, message, matches):
        # 如果文件为空则加载内容
        utils.run_in_thread(target=self.send, args=(message,))
        return True

    def send(self, message):
        if not os.stat(qiushi).st_size or not len(self.jokes):
            message.send('Tom第一次讲笑话，让我准备下，咳咳~')
            try:
                get_items()
                with open(qiushi, 'r') as fp:
                    fp.seek(0)
                    for line in fp.readlines():
                        if line.strip():
                            self.jokes.append(line)
                message.send(random.choice(self.jokes))
            except Exception as e:
                print(e)
                message.send('没有段子可以跟你讲啦~')
        else:
            # 随机发送一个笑话
            message.send(random.choice(self.jokes))

def formalize(text):
    result = ''
    lines = text.split(u'\n')
    for line in lines:
        line = line.strip()
        if len(line) == 0:
            continue
        result += line + u'\n\n'
    return result


def get_items():
    count = 0
    outfile = open(qiushi, 'w')
    for i in range(1, 2):
        url = "http://qiushibaike.com/hot/page/%d" % i
        data = urllib2.urlopen(url).readlines()
        soup = BeautifulSoup("".join(data))
        contents = soup.findAll('div', "content")
        stories = [str(text) for text in contents]
        for story in stories:
            count += 1
            logging.info("processing page %d, %d items added", i, count)
            minisoup = BeautifulSoup(story)
            text = ''.join([e for e in minisoup.recursiveChildGenerator() if isinstance(e, unicode)])
            text = urllib.unquote(unescape(text, {'&quot;':'"'}))
            text = formalize(text).encode("utf-8")
#            print >> outfile, '-' * 20 + " %05d " % count + '-' * 20 + "\n"
            print >> outfile, text
    outfile.close()


