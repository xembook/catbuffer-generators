# pylint: disable=too-few-public-methods
from inspect import getframeinfo, currentframe
from os.path import dirname, abspath, realpath, join
from mako.template import Template


class JavaStaticClassGenerator():
    """Java static class generator"""

    def __init__(self, name, schema):
        self.name = name
        self.class_output = []
        self.schema = schema

    def _get_full_file_name(self):
        filename = getframeinfo(currentframe()).filename
        path = dirname(realpath(abspath(filename)))
        return join(path, self._get_file_name())

    def _get_file_name(self):
        return '{0}.mako'.format(self.name)

    def _read_file(self):
        full_file_name = self._get_full_file_name()
        fileTemplate = Template(filename=full_file_name)
        self.class_output += [fileTemplate.render(schema=self.schema)]

    def generate(self):
        self._read_file()
        return self.class_output
