from .Helpers import indent


class TypescriptMethodGenerator:
    """Typescript method generator"""

    def __init__(self, scope, return_type, method_name, params, exception_list='', static_method=False):
        # pylint: disable-msg=too-many-arguments
        self.name = method_name
        joint_list = ', '.join(params)
        constructor_params = []
        if method_name == 'constructor':
            for param in joint_list.split(','):
                constructor_params.append('{0}'.format(param))
        parameter = ', '.join(constructor_params) if method_name == 'constructor' else ', '.join(params)
        method_line = '{0} static'.format(scope) if static_method else '{0}'.format(scope)
        if return_type:
            method_line += ' {0}({1}): {2}'.format(self.name, parameter, return_type)
        else:
            method_line += ' {0}({1})'.format(self.name, parameter)
        if exception_list:
            method_line += ' {0}'.format(exception_list)
        method_line += ' {'
        output_lines = []
        if len(method_line) > 120:
            output_lines += ['// tslint:disable-next-line: max-line-length']
        output_lines += [method_line]
        self.annotation_output = []
        self.method_output = output_lines
        self._indent_num = 1
        self.documentation_output = []

    def decrement_indent(self):
        self._indent_num -= 1

    def increment_indent(self):
        self._indent_num += 1

    def get_method(self):
        return self.documentation_output + self.annotation_output + self.method_output + ['}']

    def add_instructions(self, method_instructions, add_semicolon=True):
        for instruction in method_instructions:
            if add_semicolon:
                instruction += ';'
            if len(instruction) > 120:
                self.method_output.append(indent('// tslint:disable-next-line: max-line-length', self._indent_num))
            self.method_output.append(indent(instruction, self._indent_num))

    def add_documentations(self, method_documentations):
        for documentation in method_documentations:
            self.documentation_output.append(documentation)

    def add_annotation(self, method_annotation):
        self.annotation_output.append(method_annotation)
