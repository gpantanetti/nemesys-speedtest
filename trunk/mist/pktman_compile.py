from distutils.core import setup, Extension

import platform

if (platform.python_version_tuple()[1] == '7'):
  print 'Python 2.7'

  module = Extension('pktman',
    define_macros = [('MAJOR_VERSION', '1'),
                     ('MINOR_VERSION', '0')],
    include_dirs = ['.'],
    libraries = ['python2.7', 'pcap'],
    library_dirs = ['/usr/include/python2.7'],
    #library_dirs = ['/System/Library/Frameworks/Python.framework/Versions/2.7/include/python2.7'],
    #library_dirs = ['C:\Python27\libs', 'C:\winpcap-dev\Include'],
    sources = ['pktman.c'])
else:
  print 'Python 2.6'

  module = Extension('pktman',
    define_macros = [('MAJOR_VERSION', '1'),
                     ('MINOR_VERSION', '0')],
    include_dirs = ['.'],
    libraries = ['python2.6', 'pcap'],
    library_dirs = ['/usr/include/python2.6'],
    #library_dirs = ['/System/Library/Frameworks/Python.framework/Versions/2.6/include/python2.6'],
    #library_dirs = ['C:\Python27\libs', 'C:\winpcap-dev\Include'],
    sources = ['pktman.c'])

setup (name = 'mist',
   version = '1.1.0',
   description = 'Misura Internet Speed Test',
   author = 'Domenico Izzo',
   author_email = 'dizzo@fub.it',
   url = 'nemesys-speedtest.googlecode.com',
   long_description = '''NONE''',
   ext_modules = [module]
)