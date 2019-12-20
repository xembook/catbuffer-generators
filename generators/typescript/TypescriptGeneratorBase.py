# pylint: disable=too-few-public-methods
from abc import ABC, abstractmethod
from .Helpers import get_generated_class_name, get_comments_from_attribute, indent, format_description
from .TypescriptMethodGenerator import TypescriptMethodGenerator


class TypescriptGeneratorBase(ABC):

    # pylint: disable=too-many-instance-attributes
    def __init__(self, name, schema, class_schema):
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
        raise NotImplementedError('need to override method - typescript generator')

    @abstractmethod
    def _add_private_declarations(self):
        raise NotImplementedError('need to override method - typescript generator')

    @abstractmethod
    def _calculate_obj_size(self, new_getter):
        raise NotImplementedError('need to override method - typescript generator')

    @abstractmethod
    def _add_serialize_custom(self, serialize_method):
        raise NotImplementedError('need to override method - typescript generator')

    @abstractmethod
    def _add_load_from_binary_custom(self, load_from_binary_method):
        raise NotImplementedError('need to override method - typescript generator')

    @abstractmethod
    def _add_getters_field(self):
        raise NotImplementedError('need to override method - typescript generator')

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
        load_from_binary_method = TypescriptMethodGenerator('public',
                                                            self.generated_class_name,
                                                            'loadFromBinary',
                                                            ['payload: Uint8Array'],
                                                            '',
                                                            True)
        load_from_binary_method.add_instructions(['const byteArray = Array.from(payload)'],
                                                 True)
        self._add_load_from_binary_custom(load_from_binary_method)
        self._add_method_documentation(load_from_binary_method,
                                       'Creates an instance of {0} from binary payload.'
                                       .format(self.generated_class_name), [('payload', 'Byte payload to use to serialize the object.')],
                                       'Instance of {0}.'.format(self.generated_class_name))
        self._add_method(load_from_binary_method)

    def _add_serialize_method(self):
        serialize_method = TypescriptMethodGenerator('public',
                                                     'Uint8Array',
                                                     'serialize',
                                                     [],
                                                     '')
        serialize_method.add_instructions(['let newArray = Uint8Array.from([])'], True)
        self._add_serialize_custom(serialize_method)
        serialize_method.add_instructions(['return newArray'], True)
        self._add_method_documentation(serialize_method,
                                       'Serializes an object to bytes.',
                                       [],
                                       'Serialized bytes.')
        self._add_method(serialize_method, False)

    def _is_body_class(self):
        return self.name.endswith('Body')

    def _add_size_getter(self):
        new_getter = TypescriptMethodGenerator(
            'public', 'number', 'getSize', [])
        self._calculate_obj_size(new_getter)
        self._add_method_documentation(new_getter, 'Gets the size of the object.', [], 'Size in bytes.')
        self._add_method(new_getter)

    def _add_class_definition(self):
        class_line = get_comments_from_attribute(self.class_schema)
        if class_line is not None:
            self.class_output += [class_line]
        class_line = 'export '
        class_line += '{0} {1} '.format(
            self.class_type, self.generated_class_name)
        if self.base_class_name is not None:
            name = get_generated_class_name(self.base_class_name, self.schema[self.base_class_name], self.schema)
            self._add_required_import('{{ {0} }} from \'./{0}\''.format(name))
            class_line += 'extends {0} '.format(name)
        class_line += '{'
        self.class_output += [class_line]

    @staticmethod
    def _add_method_documentation(method_generator, description_text, parameters, return_text):
        description_text_line = format_description(description_text).replace(' \\note', '[*line-break*]\\note')
        method_generator.add_documentations(['/**'])
        for line in description_text_line.split('[*line-break*]'):
            method_generator.add_documentations([' * {0}'.format(format_description(line.replace('\\note', '@note')))])
        method_generator.add_documentations([' *'])
        if parameters:
            for name, description in parameters:
                param_text_lines = format_description(description).replace(' \\note', '[*line-break*]\\note').split('[*line-break*]')
                method_generator.add_documentations([' * @param {0} {1}'.format(name, format_description(param_text_lines[0]))])
                for line in param_text_lines[1:]:
                    method_generator.add_documentations([' * {0}'.format(format_description(line.replace('\\note', '@note')))])
        if return_text:
            return_text_lines = format_description(return_text).replace(' \\note', '[*line-break*]\\note').split('[*line-break*]')
            method_generator.add_documentations([' * @return {0}'.format(format_description(return_text_lines[0]))])
            for line in return_text_lines[1:]:
                method_generator.add_documentations([' * {0}'.format(format_description(line.replace('\\note', '@note')))])
        method_generator.add_documentations([' */'])

    def _add_required_import(self, full_class):
        if full_class not in self.required_import and '\'./number\'' not in full_class:
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
        self._add_private_declarations()
        self._create_public_declarations()
        self._add_load_from_binary_method()
        self._add_getters_field()
        self._add_size_getter()
        self._generate_interface_methods()
        self._add_serialize_method()
        endline = ['}']
        self.class_output += endline

    def generate(self):
        self._add_class_definition()
        self._generate_class_methods()

        return self.class_output
