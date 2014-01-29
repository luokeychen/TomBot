from ctypes import *

cli = cdll.LoadLibrary('./cli.so')
argc = c_int(0)
argv = c_char_p('cli')

cli.main(argc, argv)
