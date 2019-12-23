from .Helpers import get_builtin_type, indent, get_comments_from_attribute
from .Helpers import get_comments_if_present, create_enum_name
from .TypescriptGeneratorBase import TypescriptGeneratorBase


def get_type(attribute):
    return get_builtin_type(attribute['size'])


class TypescriptEnumGenerator(TypescriptGeneratorBase):
    """Typescript enum generator"""

    def __init__(self, name, schema, class_schema):
        super(TypescriptEnumGenerator, self).__init__(name, schema, class_schema)
        self.enum_values = {}
        self.class_type = 'enum'
        self._create_enum_values(self.class_schema)

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
            line += ','
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
        self.class_output += ['}']
        return self.class_output
