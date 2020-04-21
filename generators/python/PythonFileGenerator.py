import os
import logging
from datetime import datetime
from generators.Descriptor import Descriptor
from generators.python.PythonClassGenerator import PythonClassGenerator
from generators.python.PythonDefineTypeClassGenerator import PythonDefineTypeClassGenerator
from generators.python.PythonEnumGenerator import PythonEnumGenerator
from generators.python.PythonStaticClassGenerator import PythonStaticClassGenerator
from generators.python.PythonTransactionHelperGenerator import PythonTransactionHelperGenerator
from generators.python.Helpers import is_byte_type, is_enum_type, is_struct_type, add_blank_lines, CAT_TYPE, \
    TYPE_SUFFIX, NAME_VALUE_SUFFIX, log


def update_key(dict0, old_key, new_key):
    for key in dict0.keys():
        if key == old_key:
            dict0[new_key] = dict0.pop(key)
    return dict0


def append_suffix_to_key(dict0, key0, suffix):
    return update_key(dict0, key0, key0 + suffix)


def update_value(dict0, key0, old_value, new_value):
    if dict0.get(key0) == old_value:
        dict0.update({key0: new_value})
    return dict0


def append_suffix_to_value(dict0, key0, value, suffix):
    return update_value(dict0, key0, value, value + suffix)


class PythonFileGenerator:
    """Python file generator"""
    enum_class_list = {}

    @staticmethod
    def config_logging():
        try:
            os.remove('PythonGenerator.log')
        except OSError:
            pass
        logging.basicConfig(filename='PythonGenerator.log', level=logging.INFO)

    def __init__(self, schema, options):
        self.config_logging()
        log(type(self).__name__, '__init__', '*** START *** ' + datetime.now().strftime('%H:%M:%S %d-%b-%Y') + ' ***')
        self.current = None
        self.schema = schema
        self.options = options
        self.code = []
        self.imports = []

    def __iter__(self):
        self.current = self.generate()
        return self

    def __next__(self):
        self.code = []
        code, name = next(self.current)
        return Descriptor(name + '.py', code)

    def add_copyright(self, copyright_file):
        if os.path.isfile(copyright_file):
            self.code = ['#!/usr/bin/python']
            with open(copyright_file) as header:
                for line in header:
                    line = line.strip()
                    if line.startswith('/**') or line.startswith('**/'):
                        self.code += ['"""']
                    elif line.startswith('***'):
                        if len(line) > 3:
                            self.code += [line.replace('***', '   ')]
                        else:
                            self.code += [line.replace('***', '')]
                    else:
                        self.code += [line]

    def set_import(self):
        self.code += ['from __future__ import annotations']  # this must be imported before all other imports

    def update_code(self, generator):
        generated_class = generator.generate()
        for import_type in generator.get_required_imports():
            self.code += ['{0}'.format(import_type)]
        self.code += add_blank_lines(generated_class, 2)

    def _init_class(self):
        self.code = []
        self.add_copyright(self.options['copyright'])

    def _fix_shadows_builtin_name_warnings(self):
        for type_descriptor, value in self.schema.items():
            old_value = value
            value = append_suffix_to_key(value, 'type', TYPE_SUFFIX)
            value = append_suffix_to_value(value, 'name', 'type', NAME_VALUE_SUFFIX)
            value = append_suffix_to_value(value, 'name', 'id', NAME_VALUE_SUFFIX)
            value = append_suffix_to_value(value, 'name', 'hash', NAME_VALUE_SUFFIX)
            # Name with 'Size' or 'Count' suffix specify the length or size of a list (array) but this one below is an exception
            # so we suffix it to prevent it from being treated as such by this generator.
            value = append_suffix_to_value(value, 'name', 'beneficiaryCount', NAME_VALUE_SUFFIX)
            if 'layout' in value:
                for layout_dict in value.get('layout'):
                    layout_dict = append_suffix_to_key(layout_dict, 'type', TYPE_SUFFIX)
                    layout_dict = append_suffix_to_value(layout_dict, 'name', 'type', NAME_VALUE_SUFFIX)
                    layout_dict = append_suffix_to_value(layout_dict, 'name', 'id', NAME_VALUE_SUFFIX)
                    layout_dict = append_suffix_to_value(layout_dict, 'name', 'hash', NAME_VALUE_SUFFIX)
                    # Name with 'Size' or 'Count' suffix specify the length or size of a list (array) but this one below is an exception
                    # so we suffix it to prevent it from being treated as such by this generator.
                    append_suffix_to_value(layout_dict, 'name', 'beneficiaryCount', NAME_VALUE_SUFFIX)
            self.schema = update_value(self.schema, type_descriptor, old_value, value)

    def generate(self):
        filenames = []

        self._fix_shadows_builtin_name_warnings()

        for type_descriptor, value in self.schema.items():
            self._init_class()
            self.set_import()
            attribute_type = value[CAT_TYPE]

            log(type(self).__name__, 'generate',
                '{:<10}'.format(type_descriptor + ' value:' + str(value)))

            if is_byte_type(attribute_type):
                new_class = PythonDefineTypeClassGenerator(type_descriptor, self.schema, value,
                                                           PythonFileGenerator.enum_class_list)
                self.update_code(new_class)
                filenames.append(new_class.get_generated_name())
                yield self.code, new_class.get_generated_name()
            elif is_enum_type(attribute_type):
                PythonFileGenerator.enum_class_list[type_descriptor] = PythonEnumGenerator(type_descriptor,
                                                                                           self.schema, value)
            elif is_struct_type(attribute_type):
                if PythonClassGenerator.check_should_generate_class(type_descriptor):
                    new_class = PythonClassGenerator(type_descriptor, self.schema, value,
                                                     PythonFileGenerator.enum_class_list)
                    self.update_code(new_class)
                    filenames.append(new_class.get_generated_name())
                    yield self.code, new_class.get_generated_name()

        # write all the enum last just in case there are 'dynamic values'
        for type_descriptor, enum_class in PythonFileGenerator.enum_class_list.items():
            self._init_class()
            self.set_import()
            self.code += [''] + enum_class.generate()
            yield self.code, enum_class.get_generated_name()

            # write embedded transaction helper
            if type_descriptor == 'EntityType':
                helper_class_name = 'EmbeddedTransactionHelper'
                self._init_class()
                new_class = PythonTransactionHelperGenerator(helper_class_name, enum_class.enum_values, True)
                self.code += new_class.generate()
                filenames.append(helper_class_name)
                yield self.code, helper_class_name

            if type_descriptor == 'EntityType':
                helper_class_name = 'TransactionHelper'
                self._init_class()
                new_class = PythonTransactionHelperGenerator(helper_class_name, enum_class.enum_values, False)
                self.code += new_class.generate()
                filenames.append(helper_class_name)
                yield self.code, helper_class_name

        # write all the  helper files
        helper_files = ['GeneratorUtils']
        for filename in helper_files:
            self._init_class()
            self.code += ['']
            new_class = PythonStaticClassGenerator(filename)
            self.code += new_class.generate()
            filenames.append(filename)
            yield self.code, filename

        log(type(self).__name__, 'generate', '*** END *** ' + datetime.now().strftime('%H:%M:%S %d-%b-%Y') + ' ***')
