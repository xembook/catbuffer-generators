# pylint: disable=too-few-public-methods
from inspect import getframeinfo, currentframe
from os.path import dirname, abspath, realpath, join


class TypescriptStaticClassGenerator():
    """Typescript static class generator"""

    def __init__(self, name):
        self.class_output = []
        self.name = name

    def _get_full_file_name(self):
        file_name = getframeinfo(currentframe()).filename
        path = dirname(realpath(abspath(file_name)))
        return join(path, self._get_file_name())

    def _get_file_name(self):
        file_name = '{0}.ts'.format(self.name)
        return file_name

    def _read_file(self):
        full_name = self._get_full_file_name()
        with open(full_name, 'rt') as static_file:
            for line in static_file:
                self.class_output += [line.strip('\n\r')]

    def generate(self):
        self._read_file()

        return self.class_output
