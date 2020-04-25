import logging
from inspect import getframeinfo, currentframe
from os.path import dirname, abspath, realpath, join
from generators.python.Helpers import log


class PythonStaticClassGenerator:
    """Python static class generator"""

    def __init__(self, name):
        log(type(self).__name__, '__init__', ' {0}'.format(name), level=logging.DEBUG)
        self.class_output = []
        self.name = name

    def _get_full_file_name(self):
        file_name = getframeinfo(currentframe()).filename
        path = dirname(realpath(abspath(file_name)))
        return join(path, self._get_file_name())

    def _get_file_name(self):
        file_name = '{0}.py'.format(self.name)
        return file_name

    def _read_file(self):
        full_name = self._get_full_file_name()
        with open(full_name, 'rt') as static_file:
            for line in static_file:
                self.class_output += [line.strip('\n\r')]

    def generate(self):
        self._read_file()
        return self.class_output
