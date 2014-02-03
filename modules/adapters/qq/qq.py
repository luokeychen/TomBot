from ctypes import *
lib = cdll.LoadLibrary('./libqq.so')
def run():
    lib.main()

if __name__ == '__main__':
    run()

