import sys

sys.path.append('..')
from core import *
from enumerations import *
from ctypes import c_voidp

print(Lwqq.time())
Lwqq.log_level(3)
#a = 3

lc = Lwqq('1744611347','jay19880821')
lc.sync(1)
lc.login(Status.ONLINE)
ev = lc.relink()
def a():
    print(ev.raw.result)
ev.addListener(a)
lwqq_msg_send_simple(lc, 522, '3701812724', 'test test test')
lc.logout()
