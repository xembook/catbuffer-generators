# pylint: disable=too-few-public-methods
from abc import ABC, abstractmethod
from enum import Enum
import os
import re
import yaml

# note that string.capitalize also lowers [1:]
def capitalize(string):
    return string[0].upper() + string[1:] if string else string


def lookahead(iterable):
    it = iter(iterable)
    last = next(it)
    for val in it:
        # yield previous value
        yield last, False
        last = val

    # yield last value
    yield last, True


class GeneratorInterface(ABC):
    @abstractmethod
    def _add_includes(self):
        raise NotImplementedError('need to override method')

    @abstractmethod
    def _enum_header(self):
        raise NotImplementedError('need to override method')

    @abstractmethod
    def _generate_value(self, formatted_value_name, val):
        raise NotImplementedError('need to override method')

    @abstractmethod
    def _enum_footer(self):
        raise NotImplementedError('need to override method')

    @abstractmethod
    def _generate_operator(self):
        raise NotImplementedError('need to override method')


# FP from pylint, this is semi-abstract class
# pylint: disable=abstract-method
class CppGenerator(GeneratorInterface):
    def __init__(self, schema, options, name):
        super(CppGenerator, self).__init__()
        self.schema = schema
        self.code = []
        self.enum_name = name
        self.replacements = {
            'ENUM_NAME': self.enum_name
        }

        self.indent = 0
        self.hints = CppGenerator._load_hints(['namespace', 'formatting'])[self.enum_name]
        self.prepend_copyright(options['copyright'])

    @staticmethod
    def _load_hints(filenames):
        all_hints = {}
        for filename in filenames:
            with open('generators/cpp_enums/hints/{0}.yaml'.format(filename)) as input_file:
                hints = yaml.load(input_file, Loader=yaml.SafeLoader)
                for hint_key in hints:
                    if hint_key not in all_hints:
                        all_hints[hint_key] = {}

                    all_hints[hint_key][filename] = hints.get(hint_key)

        return all_hints

    def prepend_copyright(self, copyright_file):
        if os.path.isfile(copyright_file):
            with open(copyright_file) as header:
                self.code = [line.strip() for line in header]

    def generate(self):
        self._add_includes()
        self._namespace_start()
        self.indent = 1
        self._enum_header()
        self._values()
        self._enum_footer()
        self._generate_operator()
        self.indent = 0
        self._namespace_end()

        return self.code

    # region helpers

    def append(self, multiline_string, additional_replacements=None):
        for line in re.split(r'\n', multiline_string):
            # indent non-empty lines
            if line:
                replacements = {**self.replacements, **additional_replacements} if additional_replacements else self.replacements
                self.code.append('\t' * self.indent + line.format(**replacements))
            else:
                self.code.append('')

    @staticmethod
    def _is_builtin_type(typename, size):
        # uint8_t up to uint64_t are passed as 'byte' with size set to proper value
        return 'byte' == typename and size <= 8

    @staticmethod
    def _builtin_type(size, signedness):
        builtin_types = {1: 'int8_t', 2: 'int16_t', 4: 'int32_t', 8: 'int64_t'}
        builtin_type = builtin_types[size]
        return builtin_type if signedness == 'signed' else 'u' + builtin_type

    def _get_schema_field(self, field_name):
        return next(field for field in self.schema[self.enum_name]['layout'] if field['name'] == field_name)

    # endregion

    # region generate sub-methods

    def _namespace_start(self):
        self.append('// WARNING: generated from CATS file, do NOT hand-edit')
        self.append('')
        self.append('namespace catapult {{ namespace ' + self.hints['namespace'] + ' {{')
        self.append('')

    def _values(self):
        self._foreach_value(self._generate_value_proxy)

    def _namespace_end(self):
        self.append('}}}}')

    # endregion

    # region internals

    def _foreach_value(self, callback):
        for val, is_last_value in lookahead(self.schema[self.enum_name]['values']):
            callback(val, is_last_value)

    def _generate_value_proxy(self, val, is_last_value):
        formatted_value_name = '_'.join(map(capitalize, val['name'].split('_')))
        self._generate_value(formatted_value_name, val, is_last_value)

    # endregion
