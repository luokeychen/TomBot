from distutils.core import setup

setup(
    name='tombot',
    version='v1.2',
    packages=['tombot', 'tombot.rest', 'tombot.brain', 'tombot.common', 'plugins', 'plugins.user', 'plugins.ansible',
              'plugins.builtins'],
    url='',
    license='',
    author='konglx',
    author_email='jayklx@gmail.com',
    description='A robot use to automation'
)
