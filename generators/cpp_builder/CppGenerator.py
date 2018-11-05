from abc import ABC, abstractmethod
from enum import Enum
import json
import os
import re
import string

SUFFIX = 'Transaction'


class FieldKind(Enum):
    SIMPLE = 1
    BUFFER = 2
    VECTOR = 3
    UNKNOWN = 100


def tokenize(string):
    return re.findall('[A-Z][^A-Z]*', string)


def join_lower(strings):
    return ' '.join([string.lower() for string in strings])


def uncapitalize(string):
    return string[0].lower() + string[1:] if string else string


# note that string.capitalize also lowers [1:]
def capitalize(string):
    return string[0].upper() + string[1:] if string else string


def singularize(string):
    if string.endswith("es"):
        return string[:-2]

    if string.endswith("s"):
        return string[:-1]

    return string


class GeneratorInterface(ABC):
    @abstractmethod
    def _add_includes(self):
        raise NotImplementedError('need to override method')

    @abstractmethod
    def _class_header(self):
        raise NotImplementedError('need to override method')

    @abstractmethod
    def _generate_setter(self, field_kind, field, full_setter_name, param_name):
        raise NotImplementedError('need to override method')

    @abstractmethod
    def _generate_field(self, field_kind, field, builder_field_typename):
        raise NotImplementedError('need to override method')

    @abstractmethod
    def _builds(self):
        raise NotImplementedError('need to override method')

    @abstractmethod
    def _class_footer(self):
        raise NotImplementedError('need to override method')


class CppGenerator(GeneratorInterface):
    def __init__(self, schema, name):
        super(GeneratorInterface, self).__init__()
        self.schema = schema
        self.code = []
        self.transaction_name = name
        self.transaction_body_name = '{}Body'.format(name)
        short_name = name[:-len(SUFFIX)]
        self.builder_name = '{}Builder'.format(short_name)
        self.written_name = join_lower(tokenize(short_name))
        self.replacements = {
            'TRANSACTION_NAME': self.transaction_name,
            'BUILDER_NAME': self.builder_name,
            'COMMENT_NAME': self.written_name
        }

        self.indent = 0
        with open('schemas/hints.json') as input_file:
            all_hints = json.load(input_file)

        self.hints = all_hints[self.transaction_name]
        self.prepend_copyright()

    def prepend_copyright(self):
        if os.path.isfile('../HEADER.inc'):
            with open('../HEADER.inc') as header:
                self.code = [line.strip() for line in header]

    def generate(self):
        self._add_includes()
        self._namespace_start()
        self.indent = 1
        self._class_header()
        self._setters()
        self._builds()
        self._privates()
        self._class_footer()
        self.indent = 0
        self._namespace_end()

        return self.code

    # region helpers

    def _get_namespace(self, typename):
        namespace = self.hints['namespaces'].get(typename, '') if 'namespaces' in self.hints else ''
        if namespace:
            namespace += '::'

        return namespace

    def append(self, multiline_string, additional_replacements = {}):
        for line in re.split(r'\n', multiline_string):
            # indent non-empty lines
            if line:
                replacements = { **self.replacements, **additional_replacements }
                self.code.append('\t' * self.indent + line.format(**replacements))
            else:
                self.code.append('')

    def qualified_type(self, typename):
        namespace = self._get_namespace(typename)
        return namespace + typename

    def param_type(self, typename):
        # if type is simple pass by value, otherwise pass by reference
        type_descriptor = self.schema[typename]
        qualified_typename = self.qualified_type(typename)

        if 'byte' == type_descriptor['type'] and type_descriptor['size'] <= 8:
            return qualified_typename
        elif 'enum' == type_descriptor['type']:
            return qualified_typename

        return 'const {}&'.format(qualified_typename)

    @staticmethod
    def method_name(prefix, typename, param_name):
        return '{}{}({} {})'.format(prefix, capitalize(param_name), typename, uncapitalize(param_name))

    # endregion

    # region generate sub-methods

    def _namespace_start(self):
        self.append('namespace catapult {{ namespace builders {{')
        self.append('')

    def _setters(self):
        self._foreach_builder_field(self._generate_setter_proxy)

    def _privates(self):
        self._foreach_builder_field(self._generate_field_proxy)

    def _namespace_end(self):
        self.append('}}}}')

    # endregion

    # region internals

    def _foreach_builder_field(self, callback):
        for field in self.schema[self.transaction_body_name]['layout']:
            # for builder fields, skip Size or count fields, they are always used for variable data
            if field['name'].endswith('Size') or field['name'].endswith('Count'):
                continue

            callback(field)

    def _get_simple_setter_name_desc(self, field):
        """sample: void setRemoteAccountKey(const Key& remoteAccountKey)"""
        param_type = self.param_type(field['type'])
        param_name = field['name']
        return 'set', param_type, param_name

    def _get_buffer_setter_name_desc(self, field):
        """sample: void setMessage(const RawBuffer& message)"""
        assert('byte' == field['type'])
        param_type = 'const RawBuffer&'
        param_name = field['name']
        return 'set', param_type, param_name

    def _get_vector_setter_name_desc(self, field):
        """sample: void addMosaic(const Mosaic& mosaic)"""
        param_type = self.param_type(field['type'])
        param_name = singularize(field['name'])
        return 'add', param_type, param_name

    def _get_setter_name_desc(self, field_kind, field):
        getters = {
            FieldKind.SIMPLE: self._get_simple_setter_name_desc,
            FieldKind.BUFFER: self._get_buffer_setter_name_desc,
            FieldKind.VECTOR: self._get_vector_setter_name_desc
        }
        return getters[field_kind](field)

    @staticmethod
    def _get_field_kind(field):
        if 'size' not in field:
            return FieldKind.SIMPLE

        if field['size'].endswith('Size'):
            return FieldKind.BUFFER
        elif field['size'].endswith('Count'):
            return FieldKind.VECTOR

        return FieldKind.UNKNOWN

    def _generate_setter_proxy(self, field):
        field_kind = CppGenerator._get_field_kind(field)
        prefix, param_type, param_name = self._get_setter_name_desc(field_kind, field)
        full_setter_name = CppGenerator.method_name(prefix, param_type, param_name)
        self._generate_setter(field_kind, field, full_setter_name, param_name)

    def _generate_field_proxy(self, field):
        field_kind = CppGenerator._get_field_kind(field)
        qualified_typename = self.qualified_type(field['type'])
        types = {
            FieldKind.SIMPLE: '{TYPE}',
            FieldKind.BUFFER: 'std::vector<uint8_t>',
            FieldKind.VECTOR: 'std::vector<{TYPE}>'
        }
        builder_field_typename = types[field_kind].format(TYPE=qualified_typename)
        self._generate_field(field_kind, field, builder_field_typename)

    # endregion
