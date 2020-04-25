import logging
from typing import List
from generators.python.Helpers import indent, underscore_prefix, log


class PythonMethodGenerator:
    """Python method generator"""

    def __init__(self, scope: str, return_type: str, method_name: str, params: List, exception_list='', class_method=False):
        # pylint: disable-msg=too-many-arguments
        log(type(self).__name__, '__init__',
            'scope:{0} return_type:{1} method_name:{2} params:{3} exception_list:{4} class_method:{5})'
            .format(scope, return_type, method_name, str(params), exception_list, class_method),
            level=logging.DEBUG)

        self.method_annotation = []

        if class_method:
            self.add_annotation('@classmethod')
            params.insert(0, 'cls')
        else:
            params.insert(0, 'self')

        log(type(self).__name__, '__init__', 'params:'+str(params), logging.DEBUG)

        self.name = underscore_prefix(method_name) if scope in ['private', 'protected'] else method_name
        joint_list = ', '.join(params)
        constructor_params = []

        if method_name == '__init__':
            for param in joint_list.split(','):
                constructor_params.append('{0}'.format(param))

        log(type(self).__name__, '__init__', 'constructor_params:'+str(constructor_params), logging.DEBUG)

        method_header = 'def '
        parameter = ','.join(constructor_params) if method_name == '__init__' else ', '.join(params)

        log(type(self).__name__, '__init__', 'parameter:'+parameter, logging.DEBUG)

        if return_type:
            method_header += '{0}({1}) -> {2}'.format(self.name, parameter, return_type)
        else:
            method_header += '{0}({1})'.format(self.name, parameter)

        if exception_list:
            method_header += '{0}'.format(exception_list)

        method_header += ':'
        self.method_header = [method_header]
        self._indent_num = 1
        self.lint_command = []
        if len(method_header) > 100:
            self.add_linting('# pylint: disable=line-too-long')

        self.method_doc = []
        self.method_body = []

    def decrement_indent(self):
        self._indent_num -= 1

    def increment_indent(self):
        self._indent_num += 1

    def get_method(self):
        return self.method_annotation + self.lint_command + self.method_header + self.method_doc + self.method_body

    def add_instructions(self, method_instructions, add_semicolon=False):
        for instruction in method_instructions:
            if add_semicolon:
                instruction += ';'
            self.method_body.append(indent(instruction, self._indent_num))

    def add_documentations(self, method_documentations):
        for documentation in method_documentations:
            self.method_doc.append(indent(documentation, 1))

    def add_annotation(self, method_annotation):
        self.method_annotation.append(method_annotation)

    def add_linting(self, lint_command):
        self.lint_command.append(lint_command)
