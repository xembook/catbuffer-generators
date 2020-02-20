from generators.python.PythonGeneratorBase import PythonGeneratorBase
from generators.python.Helpers import get_builtin_type, indent, get_comments_from_attribute, get_comments_if_present, \
    create_enum_name, log


def get_type(attribute):
    return get_builtin_type(attribute['size'])


class PythonEnumGenerator(PythonGeneratorBase):
    """Python enum generator"""

    def __init__(self, name, schema, class_schema):
        log(type(self).__name__, '__init__')
        super(PythonEnumGenerator, self).__init__(name, schema, class_schema)
        self.enum_values = {}
        # self.required_import.add('from enum import Enum')
        self.class_type = 'class'
        self._create_enum_values(self.class_schema)

    def _add_class_definition(self):
        self.class_output += ['from enum import Enum']
        self.class_output += ['']
        self.class_output += ['']
        class_header = '{0} {1}({2}):'.format(self.class_type, self.generated_class_name, 'Enum')
        # self._add_required_import('from enum import Enum')
        self.class_output += [class_header]
        class_comment = get_comments_from_attribute(self.class_schema)
        if class_comment is not None:
            self.class_output += [indent(class_comment, 1)]
        self.class_output += ['']  # Add blank line

    def _add_private_declaration(self):
        pass

    def _create_enum_values(self, enum_attribute):
        enum_values = enum_attribute['values']
        for attribute in enum_values:
            self.add_enum_value(attribute['name'], attribute['value'],
                                get_comments_from_attribute(attribute, False))

    def _write_enum_values(self):
        enum_count = 1
        for name, value_comments in self.enum_values.items():
            value, comments = value_comments
            comment_text_line = get_comments_if_present(comments)
            if comment_text_line is not None:
                self.class_output += [indent(comment_text_line)]
            line = '{0} = {1}'.format(name.upper(), value)
            self.class_output += [indent(line)]
            enum_count += 1

    def _add_constructor(self):
        pass

    def _add_load_from_binary_custom(self, load_from_binary_method):
        pass

    def _add_serialize_custom(self, serialize_method):
        pass

    def add_enum_value(self, name, value, comments):
        self.enum_values[create_enum_name(name)] = [value, comments]

    def _create_public_declarations(self):
        pass

    def _add_private_declarations(self):
        pass

    def _calculate_obj_size(self, new_getter):
        pass

    def _add_getters_field(self):
        pass

    def generate(self):
        self._add_class_definition()
        self._write_enum_values()
        return self.class_output
