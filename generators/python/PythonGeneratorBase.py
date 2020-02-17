# pylint: disable=too-few-public-methods
import sys
import logging
from abc import ABC, abstractmethod
# from .Helpers import get_generated_class_name, get_comments_from_attribute, indent, format_description
from .Helpers import *
from .PythonMethodGenerator import PythonMethodGenerator


class PythonGeneratorBase(ABC):

    # pylint: disable=too-many-instance-attributes
    def __init__(self, name, schema, class_schema):
        logging.info(self.current_function_name(type(self).__name__))
        self.generated_class_name = get_generated_class_name(name, class_schema, schema)
        self.base_class_name = None
        self.name = name
        self.schema = schema
        self.class_output = []
        self.privates = []
        self.class_type = None
        self.class_schema = class_schema
        self.required_import = set()
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
            self._add_required_import('from .{0} import {0}'.format(classname))
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
        typename = attribute[cat_type]
        attribute_type = get_real_attribute_type(attribute)
        if attribute_type in (AttributeType.SIMPLE, AttributeType.SIZE_FIELD):
            return get_builtin_type(get_attribute_size(schema, attribute))
        if attribute_type == AttributeType.BUFFER:
            return 'bytes'
        if not is_byte_type(typename):
            typename = get_generated_class_name(typename, attribute, schema)
            if add_import:
                self._add_required_import(format_import(typename))
        if is_array(attribute_type):
            typename = 'List[{0}]'.format(typename if typename != 'EntityTypeDto' else 'int')
            if add_import:
                self._add_required_import('from typing import List')
        if attribute_type == AttributeType.FLAGS:
            return 'int'

        return typename

    def _add_required_import(self, full_class):
        if full_class not in self.required_import:  # and '.int' not in full_class:
            self.required_import.add(full_class)

    def get_required_import(self):
        import_list = list(self.required_import)
        import_list.sort()
        return import_list

    def get_generated_name(self):
        return self.generated_class_name

    def _generate_interface_methods(self):
        pass

    def _generate_class_methods(self):
        # self._add_private_declarations()  # Not applicable. Can be modified and used in future for any class variable declaration.
        self._create_public_declarations()
        self._add_load_from_binary_method()
        self._add_getters_field()
        self._add_size_getter()
        self._generate_interface_methods()
        self._add_serialize_method()
        blank_line = ['']
        self.class_output += blank_line

    def generate(self):
        self._add_class_definition()
        self._generate_class_methods()
        return self.class_output

    @classmethod
    def current_function_name(cls, classname):
        # module_name = "{:<35}".format(os.path.basename(sys._getframe().f_code.co_filename))
        current_function_name = "{:<35}".format(sys._getframe(1).f_code.co_name)
        caller_function_name = "{:<30}".format(sys._getframe(2).f_code.co_name)
        return caller_function_name + "{:<32}".format(classname) + current_function_name
