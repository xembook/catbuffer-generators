# pylint: disable=too-few-public-methods
from inspect import getframeinfo, currentframe
from os.path import dirname, abspath, realpath, join


class JavaStaticClassGenerator():
    """Java static class generator"""

    def __init__(self, name):
        self.name = name
        self.class_output = []

    def _get_full_file_name(self):
        filename = getframeinfo(currentframe()).filename
        path = dirname(realpath(abspath(filename)))
        return join(path, self._get_file_name())

    def _get_file_name(self):
        return '{0}.java'.format(self.name)

    def _read_file(self):
        full_file_name = self._get_full_file_name()
        with open(full_file_name, 'rt') as static_file:
            for line in static_file:
                self.class_output += [line.strip('\n\r')]

    def generate(self):
        self._read_file()
        return self.class_output
