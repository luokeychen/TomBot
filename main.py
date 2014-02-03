import tornado.log
import tornado.options

from modules.brain.httpd import load_scripts
def test():
    app = load_scripts()
    tornado.options.options.logging = "debug"
    tornado.log.enable_pretty_logging()
    app.listen(3000, '0.0.0.0')
    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    test()
