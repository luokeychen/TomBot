#coding: utf-8

from __future__ import unicode_literals
from __future__ import division
from __future__ import with_statement
from __future__ import print_function
from __future__ import with_statement
from __future__ import nested_scopes

import paramiko
import socket


def test():
    username = 'jagent'
    password = 'Jagent2014'
    hostname = '117.27.132.20'
    port = 53323
    tcpsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcpsock.settimeout(5)
    tcpsock.connect((hostname, port))
    trans = paramiko.Transport(tcpsock)
    trans.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(trans)
    sftp.get('/proc/stat', '/tmp/stat')

if __name__ == '__main__':
    test()


def sftp_init():
    #TODO 寻找更高效的连接方式
    username = 'jagent'
    password = 'Jagent2014'
    hostname = '117.27.132.20'
    port = 53323

    try:
        # tcpsock implements
#            tcpsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#            tcpsock.settimeout(5)
#            tcpsock.connect((hostname, port))
#            tcpsock.connect(hostname, port)
        trans = paramiko.Transport(hostname, port)
        trans.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(trans)
    except:
        pass

    finally:
#        tcpsock.close()
        trans.close()

    return sftp


class LogGraber(object):
    def __init(self, sftp, remote_path):
        pass

    def seek(self):
        pass

    def tell(self):
        pass

    def readlines(self):
        pass

    def readline(self):
        pass

    def read(self, offset, siez):
        pass
