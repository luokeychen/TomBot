#coding: utf-8

import urllib2

host = 'ftp://localhost:8000/examples'
request = urllib2.Request(host)
# ftp_handler = urllib2.FTPHandler()
# ftp_handler.ftp_open(request)
file_handler = urllib2.FileHandler()
# file_handler.parent = ftp_handler

remote_file = file_handler.file_open(request)
text = remote_file.read()
print(text)
# urllib2.FTPHandler(response)
