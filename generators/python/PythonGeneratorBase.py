import logging
from abc import ABC, abstractmethod
from generators.python.Helpers import get_generated_class_name, get_comments_from_attribute, indent, format_description, \
    is_array, get_real_attribute_type, AttributeType, get_attribute_size, get_builtin_type, is_byte_type, format_import, \
    CAT_TYPE, log
from generators.python.PythonMethodGenerator import PythonMethodGenerator


class PythonGeneratorBase(ABC):

    # pylint: disable=too-many-instance-attributes
    def __init__(self, name, schema, class_schema):
        self.generated_class_name = get_generated_class_name(name, class_schema, schema)
        log('PythonGeneratorBase', '__init__', 'generated_class_name:'+self.generated_class_name, logging.DEBUG)
        self.base_class_name = None
        self.name = name
        self.schema = schema
        self.class_output = []
        self.privates = []
        self.class_type = None
        self.class_schema = class_schema
        self.standard_lib_imports = set()
        self.app_lib_imports = set()
        self.implements_list = set()
        self.finalized_class = False

    @abstractmethod
    def _create_public_declarations(self):
        raise NotImplementedError('need to override method - python generator')

    @abstractmethod
    def _add_private_declarations(self):
        raise NotImplementedError('need to override method - python generator')

    @abstractmethod
    def _calculate_obj_size(self, new_getter):
        raise NotImplementedError('need to override method - python generator')

    @abstractmethod
    def _add_serialize_custom(self, serialize_method):
        raise NotImplementedError('need to override method - python generator')

    @abstractmethod
    def _add_load_from_binary_custom(self, load_from_binary_method):
        raise NotImplementedError('need to override method - python generator')

    @abstractmethod
    def _add_getters_field(self):
        raise NotImplementedError('need to override method - python generator')

    @staticmethod
    def _foreach_attributes(attributes, callback, context=None):
        for attr in attributes:
            if context is None:
                if callback(attr):
                    break
            else:
                if callback(attr, context):
                    break

    def _add_method(self, method, should_add_empty_line=True):
        self.class_output += [indent(line) for line in method.get_method()]
        if should_add_empty_line:
            self.class_output += ['']

    def _add_load_from_binary_method(self):
        load_from_binary_method = PythonMethodGenerator('', self.generated_class_name, 'loadFromBinary', ['payload: bytes'], '', True)
        load_from_binary_method.add_instructions(['bytes_ = bytes(payload)'])
        self._add_load_from_binary_custom(load_from_binary_method)
        self._add_method_documentation(load_from_binary_method,
                                       'Creates an instance of {0} from binary payload.'
                                       .format(self.generated_class_name), [('payload', 'Byte payload to use to serialize the object.')],
                                       'Instance of {0}.'.format(self.generated_class_name))
        self._add_method(load_from_binary_method)

    def _add_serialize_method(self):
        serialize_method = PythonMethodGenerator('', 'bytes', 'serialize', [], '')
        serialize_method.add_instructions(['bytes_ = bytes()'])
        self._add_serialize_custom(serialize_method)
        serialize_method.add_instructions(['return bytes_'])
        self._add_method_documentation(serialize_method, 'Serializes an object to bytes.', [], 'Serialized bytes.')
        self._add_method(serialize_method, False)

    def _is_body_class(self):
        return self.name.endswith('Body')

    def _add_size_getter(self):
        new_getter = PythonMethodGenerator('', 'int', 'getSize', [])
        self._calculate_obj_size(new_getter)
        self._add_method_documentation(new_getter, 'Gets the size of the object.', [], 'Size in bytes.')
        self._add_method(new_getter)

    def _add_class_definition(self):
        class_header = '{0} {1}'.format(self.class_type, self.generated_class_name)
        if self.base_class_name is not None:
            classname = get_generated_class_name(self.base_class_name, self.schema[self.base_class_name], self.schema)
            self._add_app_lib_import(format_import(classname))
            class_header += '({0})'.format(classname)
        class_header += ':'
        self.class_output += [class_header]
        class_comment = get_comments_from_attribute(self.class_schema)
        if class_comment is not None:
            self.class_output += [indent(class_comment, 1)]
        self.class_output += ['']  # Add a blank line

    @staticmethod
    def _add_method_documentation(method_generator, description_text, parameters, return_text):
        description_text_line = format_description('"""' + description_text).replace(' \\note', '[*line-break*]\\note')
        for line in description_text_line.split('[*line-break*]'):
            method_generator.add_documentations(['{0}'.format(format_description(line.replace('\\note', '@note')))])
        if parameters:
            method_generator.add_documentations(['Args:'])
            for name, description in parameters:
                param_text_lines = format_description(description).replace(' \\note', '[*line-break*]\\note').split('[*line-break*]')
                method_generator.add_documentations([indent('{0}: {1}'.format(name, format_description(param_text_lines[0])))])
                for line in param_text_lines[1:]:
                    method_generator.add_documentations(['{0}'.format(format_description(line.replace('\\note', '@note')))])
        if return_text:
            method_generator.add_documentations(['Returns:'])
            return_text_lines = format_description(return_text).replace(' \\note', '[*line-break*]\\note').split('[*line-break*]')
            method_generator.add_documentations([indent('{0}'.format(format_description(return_text_lines[0])))])
            for line in return_text_lines[1:]:
                method_generator.add_documentations(['{0}'.format(format_description(line.replace('\\note', '@note')))])
        method_generator.add_documentations(['"""'])

    def get_generated_type(self, schema, attribute, add_import=False):
        attribute_type = get_real_attribute_type(attribute)
        return_type = None
        if attribute_type in (AttributeType.SIMPLE, AttributeType.SIZE_FIELD):
            return_type = get_builtin_type(get_attribute_size(schema, attribute))
        if attribute_type == AttributeType.BUFFER:
            return_type = 'bytes'
        if attribute_type == AttributeType.FLAGS:
            return_type = 'int'

        if return_type is None:
            cat_type = attribute[CAT_TYPE]
            if not is_byte_type(cat_type):
                classname = get_generated_class_name(cat_type, attribute, schema)
                if is_array(attribute_type):
                    return_type = 'List[{0}]'.format(classname if classname != 'EntityTypeDto' else 'int')
                    if add_import:
                        self._add_standard_lib_import('from typing import List')
                if add_import and 'int' not in str(return_type):
                    self._add_app_lib_import(format_import(classname))
                if return_type is None:
                    return_type = classname

        log('PythonGeneratorBase', 'get_generated_type', 'attribute_type: ' + str(attribute_type) + ' return_type: ' + str(return_type))
        return return_type

    def _add_standard_lib_import(self, import_statement):
        if import_statement not in self.standard_lib_imports:
            self.standard_lib_imports.add(import_statement)

    def _add_app_lib_import(self, full_class):
        if full_class not in self.app_lib_imports:
            self.app_lib_imports.add(full_class)

    def get_required_imports(self):
        import_list = list(self.standard_lib_imports)
        import_list.sort()
        app_imports = list(self.app_lib_imports)
        app_imports.sort()
        import_list.extend(app_imports)
        return import_list

    def get_generated_name(self):
        return self.generated_class_name

    def _generate_interface_methods(self):
        pass

    def _generate_class_methods(self):
        self._create_public_declarations()
        self._add_load_from_binary_method()
        self._add_getters_field()
        self._add_size_getter()
        self._generate_interface_methods()
        self._add_serialize_method()

    def generate(self):
        self._add_class_definition()
        self._generate_class_methods()
        return self.class_output
