from .Helpers import create_enum_name, get_default_value, get_comment_from_name
from .Helpers import get_real_attribute_type, TypeDescriptorDisposition, get_attribute_if_size, get_byte_convert_method_name
from .Helpers import get_generated_class_name, indent, get_attribute_size, get_builtin_type, is_fill_array
from .Helpers import get_generated_type, get_attribute_property_equal, AttributeType, is_byte_type, is_var_array
from .Helpers import get_read_method_name, is_enum_type, is_reserved_field, is_array
from .Helpers import get_comments_from_attribute, format_import
from .TypescriptGeneratorBase import TypescriptGeneratorBase
from .TypescriptMethodGenerator import TypescriptMethodGenerator


def capitalize_first_character(string):
    return string[0].upper() + string[1:]


# pylint: disable=too-many-instance-attributes
class TypescriptClassGenerator(TypescriptGeneratorBase):
    """Typescript class generator"""

    def __init__(self, name, schema, class_schema, enum_list):
        super(TypescriptClassGenerator, self).__init__(name, schema, class_schema)
        self.enum_list = enum_list
        self.class_type = 'class'
        self.conditional_param_list = []
        self.condition_param = []
        self.load_from_binary_atrribute_list = []
        self._add_required_import(format_import('GeneratorUtils'))
        self.condition_binary_declare_map = {}
        self._load_from_binary_condition_lines = []

        if 'layout' in self.class_schema:
            # Find base class
            self._foreach_attributes(
                self.class_schema['layout'], self._find_base_callback)
            # Find any condition variables
            self._recursive_attribute_iterator(
                self.name, self._create_condition_list, self.conditional_param_list, [])

    @staticmethod
    def _is_inline_class(attribute):
        return 'disposition' in attribute and attribute['disposition'] == TypeDescriptorDisposition.Inline.value

    def _find_base_callback(self, attribute):
        if self._is_inline_class(attribute) and self.check_should_generate_class(attribute['type']):
            self.base_class_name = attribute['type']
            self.finalized_class = True
            return True
        return False

    def _create_condition_list(self, attribute_value, condition_list):
        if self._is_conditional_attribute(attribute_value):
            condition_list.append(attribute_value)

    @staticmethod
    def _is_conditional_attribute(attribute_value):
        return 'condition' in attribute_value

    def _should_declaration(self, attribute_value):
        return not self.is_count_size_field(attribute_value) and attribute_value['name'] != 'size'

    def _get_body_class_name(self):
        body_name = self.name if not self.name.startswith('Embedded') else self.name[8:]
        # Special case for AggregateTransactionBody
        if self.name.startswith('Aggregate') and self.name.endswith('Transaction'):
            body_name = 'AggregateTransaction'
        return '{0}Body'.format(body_name)

    def _add_private_declarations(self):
        self._recursive_attribute_iterator(self.name, self._create_private_declaration, self.class_output,
                                           [self.base_class_name, self._get_body_class_name()])
        self.class_output += ['']

    def _add_required_import_if_needed(self, var_type):
        if var_type not in ['number', 'Uint8Array', 'number[]']:
            self._add_required_import(format_import(var_type))

    def _create_private_declaration(self, attribute, output):
        if not self.is_count_size_field(attribute):
            line = get_comments_from_attribute(attribute)
            if line is not None:
                output += [indent(line)]
            attribute_name = attribute['name']
            var_type = get_generated_type(self.schema, attribute)
            is_conditional = self._is_attribute_conditional(attribute, self.conditional_param_list)
            self._add_required_import_if_needed(var_type)
            output += [indent('{1}{2}{0}{3};'.format('' if attribute['name'] == 'size' else ': ' + var_type,
                                                     attribute_name, '?' if is_conditional else '',
                                                     ' = 0' if attribute['name'] == 'size' else ''))]

    @staticmethod
    def _get_generated_getter_name(attribute):
        return 'get{0}'.format(capitalize_first_character(attribute))

    @staticmethod
    def _add_simple_getter(attribute, getter):
        getter.add_instructions(
            ['return this.{0}'.format(attribute['name'])])

    @staticmethod
    def _add_buffer_getter(attribute, getter):
        getter.add_instructions(
            ['return this.{0}'.format(attribute['name'])])

    # pylint: disable-msg=too-many-arguments
    def _add_if_condition_for_variable_if_needed(self, attribute, code_wirter, object_prefix,
                                                 if_condition, code_lines, add_var_declare=False, add_semicolon=True):
        if attribute['condition_operation'] == 'has':
            if_condition = '&'

        condition_type_attribute = get_attribute_property_equal(self.schema, self.class_schema['layout'], 'name', attribute['condition'])
        condition_type = '{0}.{1}'.format(get_generated_class_name(condition_type_attribute['type'], condition_type_attribute, self.schema),
                                          create_enum_name(attribute['condition_value']))
        if add_var_declare:
            code_wirter.add_instructions(['let {0}'.format(attribute['name'])], True)
        code_wirter.add_instructions(['if ({0}{1} {2} {3}) {{'.format(object_prefix, attribute['condition'], if_condition, condition_type)],
                                     False)

        for line in code_lines:
            code_wirter.add_instructions([indent(line)], add_semicolon)
        code_wirter.add_instructions(['}'], False)

    def _add_if_condition_for_variable_if_needed_load_binary(self, attribute, code_wirter, object_prefix,
                                                             if_condition, add_var_declare=False, add_semicolon=True):
        if attribute['condition_operation'] == 'has':
            if_condition = '&'

        condition_type_attribute = get_attribute_property_equal(self.schema, self.class_schema['layout'], 'name', attribute['condition'])
        condition_type = '{0}.{1}'.format(get_generated_class_name(condition_type_attribute['type'], condition_type_attribute, self.schema),
                                          create_enum_name(attribute['condition_value']))
        self._add_load_from_binary_condition_not_declared(attribute, code_wirter, add_semicolon)

        if add_var_declare:
            self._load_from_binary_condition_lines += ['let {0};'.format(attribute['name'])]
        self._load_from_binary_condition_lines += ['if ({0}{1} {2} {3}) {{'.format(
            object_prefix, attribute['condition'], if_condition, condition_type)]
        self._load_from_binary_condition_lines += [indent('{2}{0} = {1}.loadFromBinary({3});'.format(
            attribute['name'], get_generated_class_name(attribute['type'], attribute, self.schema),
            '' if self._is_conditional_attribute(attribute) else 'const ',
            attribute['condition'] + 'ConditionBytes'))]
        self._load_from_binary_condition_lines += ['}']

    def _add_load_from_binary_condition_not_declared(self, attribute, code_wirter, add_semicolon=True):
        if attribute['condition'] not in self.condition_binary_declare_map.keys():
            code_wirter.add_instructions(['const {0}ConditionBytes = Uint8Array.from(byteArray.slice(0, {1}))'.format(
                attribute['condition'], str(get_attribute_size(self.schema, attribute)))], add_semicolon)
            code_wirter.add_instructions(['byteArray.splice(0, {0})'.format(
                str(get_attribute_size(self.schema, attribute)))], add_semicolon)
        self.condition_binary_declare_map[attribute['condition']] = True

    def _add_method_condition(self, attribute, method_code_writer):
        if 'condition' in attribute:
            lines = ['throw new Error(\'{0} is not set to {1}.\')'.format(
                attribute['condition'], create_enum_name(attribute['condition_value']))]
            self._add_if_condition_for_variable_if_needed(attribute, method_code_writer, 'this.', '!==', lines)

    def _add_getter(self, attribute, schema):
        return_type = get_generated_type(schema, attribute)
        attribute_name = attribute['name']
        self._add_required_import_if_needed(return_type)
        if attribute in self.conditional_param_list:
            return_type += ' | undefined'
        getter = TypescriptMethodGenerator('public', return_type, self._get_generated_getter_name(attribute_name), [])

        if 'aggregate_class' in attribute:
            # Pass through
            getter.add_instructions(
                ['return this.{0}.{1}()'.format(self._get_fromatted_type_name(attribute['aggregate_class']),
                                                self._get_generated_getter_name(attribute_name))])
        else:
            self._add_method_condition(attribute, getter)
            getters = {
                AttributeType.SIMPLE: self._add_simple_getter,
                AttributeType.BUFFER: self._add_buffer_getter,
                AttributeType.ARRAY: self._add_simple_getter,
                AttributeType.CUSTOM: self._add_simple_getter,
                AttributeType.FLAGS: self._add_simple_getter,
                AttributeType.FILL_ARRAY: self._add_simple_getter,
                AttributeType.VAR_ARRAY: self._add_simple_getter
            }
            attribute_kind = get_real_attribute_type(attribute)
            getters[attribute_kind](attribute, getter)

        # If the comments is empty then just use name in the description
        description = get_comments_from_attribute(attribute, False)
        self._add_method_documentation(getter, 'Gets {0}.'
                                       .format(description), [], description)
        self._add_method(getter)

    @staticmethod
    def _add_simple_setter(attribute, setter):
        setter.add_instructions(['this.{0} = {0}'.format(attribute['name'])])

    @staticmethod
    def _add_array_setter(attribute, setter):
        setter.add_instructions(['this.{0} = {0}'.format(attribute['name'])])

    @staticmethod
    def _add_buffer_setter(attribute, setter):
        attribute_name = attribute['name']
        setter.add_instructions(['this.{0} = {0}'.format(attribute_name)])

    @staticmethod
    def _serialize_attribute_buffer(attribute, serialize_method):
        attribute_name = attribute['name']
        method = 'this.{0}'.format(attribute_name)
        line = 'newArray = GeneratorUtils.concatTypedArrays(newArray, {0});'.format(method)
        serialize_method.add_instructions([line], False)

    @staticmethod
    def _get_serialize_name(attribute_name):
        return '{0}Bytes'.format(attribute_name)

    @staticmethod
    def _should_add_base_on_condition(attribute, condition_attribute_list):
        attribute_name = attribute['name']
        if condition_attribute_list:
            for condition_attribute in condition_attribute_list:
                if condition_attribute['condition'] == attribute_name and condition_attribute['condition_operation'] == 'equals':
                    return False
        return True

    @staticmethod
    def _is_attribute_conditional(attribute, condition_attribute_list):
        if condition_attribute_list:
            for condition in condition_attribute_list:
                if attribute['name'] == condition['name'] and attribute['type'] == condition['type']:
                    return True
        return False

    @staticmethod
    def _get_condition_factory_method_name(condition_attribute):
        condition_value = create_enum_name(condition_attribute['condition_value']).lower()
        return 'create' + capitalize_first_character(condition_value)

    @staticmethod
    def check_should_generate_class(name):
        return ((name.startswith('Embedded') and not name.endswith('Header'))
                or 'Mosaic' in name
                or name.startswith('Account')
                or name.startswith('Address')
                or name.startswith('Global')
                or name.startswith('Multisig')
                or name.startswith('Metadata')
                or name.startswith('HeightActivity')
                or name.startswith('ImportanceSnapshot')
                or name.startswith('PinnedVotingKey')
                or 'VrfProof' in name
                or 'Namespace' in name
                or 'Restrict' in name
                or 'Lock' in name
                or name.endswith('Info')
                or name.startswith('Block')
                or name.endswith('Transaction')
                or (name.endswith('Body') and name != 'EntityBody')
                or 'Receipt' in name
                or name.endswith('Modification')
                or name.endswith('Cosignature'))

    def _add_size_values(self, attribute, method_writer):
        attribute_kind = get_real_attribute_type(attribute)
        line = 'size += '
        if attribute_kind == AttributeType.SIMPLE:
            line += '{0}; // {1}'.format(attribute['size'], attribute['name'])
        elif attribute_kind == AttributeType.BUFFER:
            line += 'this.{0}.length;'.format(attribute['name'])
        elif attribute_kind in (AttributeType.ARRAY, AttributeType.VAR_ARRAY, AttributeType.FILL_ARRAY):
            line = ''
            if attribute['type'] == 'EntityType':
                line += 'this.{0}.forEach(() => size += 2);'.format(attribute['name'])
            elif attribute['type'] == 'EmbeddedTransaction':
                line += 'this.{0}.forEach((o) => size += EmbeddedTransactionHelper.serialize(o).length);'.format(attribute['name'])
            else:
                line += 'this.{0}.forEach((o) => size += o.getSize());'.format(attribute['name'])
        elif attribute_kind == AttributeType.FLAGS:
            line += self._get_custom_attribute_size_getter(attribute)
        else:
            line += self._get_custom_attribute_size_getter(attribute)

        self._add_attribute_condition_if_needed(attribute, method_writer, 'this.', [line], False, False, False)

    def _get_custom_attribute_size_getter(self, attribute):
        for type_descriptor, value in self.schema.items():
            attribute_type = value['type']
            attribute_name = type_descriptor
            if is_enum_type(attribute_type) and attribute_name == attribute['type']:
                return '{0}; // {1}'.format(value['size'], attribute['name'])
        is_condition = attribute in self.conditional_param_list
        return 'this.{0}{1}.getSize();'.format(attribute['name'],
                                               '!' if is_condition else '')

    def _calculate_obj_size(self, new_getter):
        return_type = 'number'
        if self.base_class_name is not None:
            new_getter.add_instructions(['let size: {0} = super.getSize()'.format(return_type)])
        else:
            new_getter.add_instructions(['let size = 0'])
        self._recursive_attribute_iterator(self.name, self._add_size_values, new_getter,
                                           [self.base_class_name, self._get_body_class_name()])
        new_getter.add_instructions(['return size'])

    def _add_getters(self, attribute, schema):
        if self._should_declaration(attribute):
            self._add_getter(attribute, schema)

    @staticmethod
    def _get_fromatted_type_name(type_name):
        return type_name[0].lower() + type_name[1:]

    def _recursive_attribute_iterator(self, class_name, callback, context, ignore_inline_class):
        generated_class = (class_name != self.name and self.check_should_generate_class(class_name))
        for attribute_val in self.schema[class_name]['layout']:
            if generated_class:
                attribute_val['aggregate_class'] = class_name

            if 'disposition' in attribute_val:
                inline_class_type = attribute_val['type']
                if attribute_val['disposition'] == TypeDescriptorDisposition.Inline.value:
                    if self.check_should_generate_class(inline_class_type):
                        # Class was grenerated so it can be declare aggregate
                        attribute_val['name'] = self._get_fromatted_type_name(inline_class_type)
                        if (self.base_class_name == inline_class_type and
                                self.base_class_name in ignore_inline_class):
                            continue  # skip the base class
                        if inline_class_type in ignore_inline_class:
                            callback(attribute_val, context)
                            continue

                    self._recursive_attribute_iterator(inline_class_type, callback, context, ignore_inline_class)
                elif attribute_val['disposition'] == TypeDescriptorDisposition.Const.value:
                    # add dynamic enum if present in this class
                    enum_name_value = attribute_val['type']
                    if enum_name_value in self.enum_list:
                        self.enum_list[enum_name_value].add_enum_value(
                            self.generated_class_name, attribute_val['value'],
                            get_comment_from_name(self.generated_class_name))
                    continue
                elif is_var_array(attribute_val) or is_fill_array(attribute_val):
                    callback(attribute_val, context)
                    continue
            else:
                callback(attribute_val, context)

    def _init_other_attribute_in_condition(self, attribute, obj_prefix, code_lines):
        if 'condition' in attribute:
            for condition_attribute in self.conditional_param_list:
                if attribute['name'] != condition_attribute['name']:
                    code_lines.append('{0}{1} = {2}'.format(obj_prefix, condition_attribute['name'], get_default_value(attribute)))

    def _add_attribute_condition_if_needed(self, attribute, method_writer, obj_prefix, code_lines, is_load_from_binary=False,
                                           add_var_declare=False, add_semicolon=True):
        if 'condition' in attribute:
            if is_load_from_binary:
                self._add_if_condition_for_variable_if_needed_load_binary(attribute, method_writer, obj_prefix, '===',
                                                                          add_var_declare, add_semicolon)
            else:
                self._add_if_condition_for_variable_if_needed(attribute, method_writer, obj_prefix, '===',
                                                              code_lines, add_var_declare, add_semicolon)
        else:
            method_writer.add_instructions(code_lines, add_semicolon)

    def _load_from_binary_simple(self, attribute, load_from_binary_method):
        size = get_attribute_size(self.schema, attribute)
        const_delaration = 'GeneratorUtils.getBytes(Uint8Array.from(byteArray), {0})'.format(size)
        read_method_name = get_byte_convert_method_name(size).format(const_delaration)
        lines = ['{2}{0} = {1}'.format(attribute['name'], read_method_name, '' if self._is_conditional_attribute(attribute) else 'const ')]
        lines += ['byteArray.splice(0, {0})'.format(size)]
        self._add_attribute_condition_if_needed(attribute, load_from_binary_method, '', lines, True, True)
        if not self.load_from_binary_atrribute_list:
            load_from_binary_method.add_instructions(['return new {0}({1})'.format(self.generated_class_name, attribute['name'])])

    def _load_from_binary_buffer(self, attribute, load_from_binary_method):
        size = get_attribute_size(self.schema, attribute)
        if size != 0:
            lines = ['{2}{0} = GeneratorUtils.getBytes(Uint8Array.from(byteArray), {1})'
                     .format(attribute['name'], size, '' if self._is_conditional_attribute(attribute) else 'const ')]
            lines += ['byteArray.splice(0, {0})'.format(size)]
        else:
            lines = ['{1}{0} = Uint8Array.from(byteArray)'
                     .format(attribute['name'], '' if self._is_conditional_attribute(attribute) else 'const ')]
        load_from_binary_method.add_instructions(lines)
        if not self.load_from_binary_atrribute_list:
            load_from_binary_method.add_instructions(['return new {0}({1})'.format(self.generated_class_name, attribute['name'])])

    def _load_from_binary_array(self, attribute, load_from_binary_method):
        attribute_typename = attribute['type']
        attribute_sizename = '(Array.isArray({0}) ? GeneratorUtils.compact({0}) : {0})'.format(attribute['size'])
        attribute_name = attribute['name']
        var_type = get_generated_type(self.schema, attribute)
        load_from_binary_method.add_instructions(['const {0}{1} = []'
                                                  .format(attribute_name,
                                                          '' if attribute_typename in ['number', 'Uint8Array'] else
                                                          ': ' + var_type)])
        load_from_binary_method.add_instructions(['for (let i = 0; i < {0}; i++) {{'.format(attribute_sizename)], False)

        if is_byte_type(attribute_typename):
            const_delaration = 'GeneratorUtils.getBytes(Uint8Array.from(byteArray), 1)'
            read_method_name = get_byte_convert_method_name(1).format(const_delaration)
            load_from_binary_method.add_instructions(
                [indent('{1}item = {0}'.format(read_method_name, '' if self._is_conditional_attribute(attribute) else 'const '))])
            load_from_binary_method.add_instructions([indent('{0}.add(stream.{1}())'.format(attribute_name, get_read_method_name(1)))])
        else:
            if attribute_typename == 'EntityType':
                entity_type_const_delaration = 'GeneratorUtils.getBytes(Uint8Array.from(byteArray), 2)'
                read_method_name = get_byte_convert_method_name(2).format(entity_type_const_delaration)
                load_from_binary_method.add_instructions(
                    [indent('{1}item = {0}'
                            .format(read_method_name,
                                    '' if self._is_conditional_attribute(attribute) else 'const '))])
            else:
                load_from_binary_method.add_instructions(
                    [indent('{1}item = {0}.loadFromBinary(Uint8Array.from(byteArray))'
                            .format(get_generated_class_name(attribute_typename, attribute, self.schema),
                                    '' if self._is_conditional_attribute(attribute) else 'const '))])
        load_from_binary_method.add_instructions([indent('{0}.push(item)'.format(attribute_name))])
        load_from_binary_method.add_instructions([indent('byteArray.splice(0, {0})'.format(
            'item.getSize()' if attribute_typename != 'EntityType' else '2'))])
        load_from_binary_method.add_instructions(['}'], False)

    def _load_from_binary_custom(self, attribute, load_from_binary_method):
        is_custom_type_enum = False
        customer_enum_size = 0
        for type_descriptor, value in self.schema.items():
            enum_attribute_type = value['type']
            enum_attribute_name = type_descriptor
            if is_enum_type(enum_attribute_type) and enum_attribute_name == attribute['type']:
                is_custom_type_enum = True
                customer_enum_size = value['size']

        if is_custom_type_enum and customer_enum_size > 0:
            const_declare = 'GeneratorUtils.getBytes(Uint8Array.from(byteArray), {0})'.format(customer_enum_size)
            enum_method = get_byte_convert_method_name(customer_enum_size).format(const_declare)
            lines = ['{2}{0} = {1}'.format(attribute['name'], enum_method,
                                           '' if self._is_conditional_attribute(attribute) else 'const ')]
            lines += ['byteArray.splice(0, {0})'.format(customer_enum_size)]
        else:
            lines = ['{2}{0} = {1}.loadFromBinary(Uint8Array.from(byteArray))'
                     .format(attribute['name'], get_generated_class_name(attribute['type'], attribute, self.schema),
                             '' if self._is_conditional_attribute(attribute) else 'const ')]
            lines += ['byteArray.splice(0, {0}.getSize())'.format(attribute['name'])]
        self._add_attribute_condition_if_needed(attribute, load_from_binary_method, '', lines, True, True)

    def _load_from_binary_flags(self, attribute, load_from_binary_method):
        size = get_attribute_size(self.schema, attribute)
        const_declare = 'GeneratorUtils.getBytes(Uint8Array.from(byteArray), {0})'.format(size)
        read_method_name = get_byte_convert_method_name(size).format(const_declare)
        lines = ['{2}{0} = {1}'.format(attribute['name'], read_method_name, '' if self._is_conditional_attribute(attribute) else 'const ')]
        lines += ['byteArray.splice(0, {0})'.format(size)]
        self._add_attribute_condition_if_needed(attribute, load_from_binary_method, '', lines, True, True)
        if len(self.load_from_binary_atrribute_list) <= 1:
            load_from_binary_method.add_instructions(['return new {0}({1})'.format(self.generated_class_name, attribute['name'])])

    def _load_from_binary_field(self, attribute, load_from_binary_method):
        attribute_name = attribute['name']
        load_from_binary_method.add_instructions(
            ['final {0} {1};'.format(get_generated_type(self.schema, attribute), attribute_name)])

    def _load_from_binary_var_fill_array(self, attribute, load_from_binary_method):
        attribute_typename = attribute['type']
        attribute_sizename = attribute['size']
        if attribute_sizename == 0:
            attribute_sizename = 'byteArray.length'
        attribute_name = attribute['name']
        var_type = get_generated_type(self.schema, attribute)
        load_from_binary_method.add_instructions(['let {0}ByteSize = {1}'.format(attribute_name, attribute_sizename)])
        load_from_binary_method.add_instructions(['const {0}{1} = []'
                                                  .format(attribute_name,
                                                          '' if attribute_typename in ['number', 'Uint8Array'] else
                                                          ': ' + var_type)])
        load_from_binary_method.add_instructions(['while ({0}ByteSize > 0) {{'.format(attribute_name)], False)
        serializer_name = get_generated_class_name(attribute_typename, attribute, self.schema)
        item_size = 'const itemSize = item.getSize()'
        if attribute_typename == 'EmbeddedTransaction':
            serializer_name = 'EmbeddedTransactionHelper'
            self.required_import.add('{{ {0} }} from \'./{0}\''.format(serializer_name))
            item_size = 'const itemSize = item.getSize() + GeneratorUtils.getTransactionPaddingSize(item.getSize(), 8)'

        load_from_binary_method.add_instructions(
            [indent('{1}item = {0}.loadFromBinary(Uint8Array.from(byteArray))'
                    .format(serializer_name, '' if self._is_conditional_attribute(attribute) else 'const '))])
        load_from_binary_method.add_instructions([indent('{0}.push(item)'.format(attribute_name))])
        load_from_binary_method.add_instructions([indent(item_size)])
        load_from_binary_method.add_instructions([indent('{0}ByteSize -= itemSize'.format(attribute_name))])
        load_from_binary_method.add_instructions([indent('byteArray.splice(0, itemSize)')])
        load_from_binary_method.add_instructions(['}'], False)

    @staticmethod
    def is_count_size_field(field):
        return (field['name'].endswith('Size') or
                (field['name'].endswith('Count') and 'beneficiaryCount' not in field['name']))

    def _generate_load_from_binary_attributes(self, attribute, load_from_binary_method):
        if self.is_count_size_field(attribute):
            const_declare = 'GeneratorUtils.getBytes(Uint8Array.from(byteArray), {0})'.format(attribute['size'])
            size_method = get_byte_convert_method_name(attribute['size']).format(const_declare)
            lines = ['const {0} = {1}'.format(attribute['name'], size_method)]
            lines += ['byteArray.splice(0, {0})'.format(attribute['size'])]
            load_from_binary_method.add_instructions(lines)
        else:
            load_attribute = {
                AttributeType.SIMPLE: self._load_from_binary_simple,
                AttributeType.BUFFER: self._load_from_binary_buffer,
                AttributeType.ARRAY: self._load_from_binary_array,
                AttributeType.CUSTOM: self._load_from_binary_custom,
                AttributeType.FLAGS: self._load_from_binary_flags,
                AttributeType.SIZE_FIELD: self._load_from_binary_field,
                AttributeType.FILL_ARRAY: self._load_from_binary_var_fill_array,
                AttributeType.VAR_ARRAY: self._load_from_binary_var_fill_array
            }

            attribute_kind = get_real_attribute_type(attribute)
            load_attribute[attribute_kind](attribute, load_from_binary_method)

    def _serialize_attribute_simple(self, attribute, serialize_method):
        if self.name == 'Receipt' and attribute['name'] == 'size':
            self._add_attribute_condition_if_needed(attribute, serialize_method, 'this.', [], False, False)
        else:
            size = get_attribute_size(self.schema, attribute)
            method = '{0}(this.{1}(), {2})'.format(get_read_method_name(size),
                                                   self._get_generated_getter_name(attribute['name']),
                                                   size) if size < 8 else '{0}(this.{1}())'.format(get_read_method_name(size),
                                                                                                   self._get_generated_getter_name(
                                                                                                       attribute['name']))
            lines = ['const {0}Bytes = {1}'.format(attribute['name'], method)]
            lines += ['newArray = GeneratorUtils.concatTypedArrays(newArray, {0})'.format(attribute['name']+'Bytes')]
            self._add_attribute_condition_if_needed(attribute, serialize_method, 'this.', lines, False, False)

    def _serialize_attribute_array(self, attribute, serialize_method):
        attribute_typename = attribute['type']
        attribute_name = attribute['name']
        serialize_method.add_instructions(['this.{0}.forEach((item) => {{'.format(attribute_name)], False)

        if is_byte_type(attribute_typename):
            byte_method = 'this.{0}'.format(attribute_name)
            byte_line = 'newArray = GeneratorUtils.concatTypedArrays(newArray, {0});'.format(byte_method)
            serialize_method.add_instructions(
                [indent(byte_line)])
        else:
            attribute_bytes_name = self._get_serialize_name(attribute_name)
            if attribute_typename == 'EntityType':
                serialize_method.add_instructions(
                    [indent('const {0} = GeneratorUtils.uintToBuffer(item, 2)'.format(attribute_bytes_name))])
            elif attribute_typename == 'EmbeddedTransaction':
                serialize_method.add_instructions(
                    [indent('const {0} = EmbeddedTransactionHelper.serialize(item)'.format(attribute_bytes_name))])
            else:
                serialize_method.add_instructions(
                    [indent('const {0} = item.serialize()'.format(attribute_bytes_name))])
            serialize_method.add_instructions(
                [indent('newArray = GeneratorUtils.concatTypedArrays(newArray, {0})'.format(attribute_bytes_name))])
        serialize_method.add_instructions(['})'], True)

    def _serialize_attribute_custom(self, attribute, serialize_method):
        attribute_name = attribute['name']
        attribute_bytes_name = self._get_serialize_name(attribute_name)
        is_custom_type_enum = False
        customer_enum_size = 0
        is_condition = attribute in self.conditional_param_list
        for type_descriptor, value in self.schema.items():
            enum_attribute_type = value['type']
            enum_attribute_name = type_descriptor
            if is_enum_type(enum_attribute_type) and enum_attribute_name == attribute['type']:
                is_custom_type_enum = True
                customer_enum_size = value['size']
        if is_custom_type_enum and customer_enum_size > 0:
            lines = ['const {0} = GeneratorUtils.uintToBuffer(this.{1}, {2})'
                     .format(attribute_bytes_name, attribute_name, customer_enum_size)]
        else:
            lines = ['const {0} = this.{1}{2}.serialize()'.format(attribute_bytes_name,
                                                                  attribute_name,
                                                                  '!' if is_condition else '')]
        lines += ['newArray = GeneratorUtils.concatTypedArrays(newArray, {0})'.format(attribute_bytes_name)]
        self._add_attribute_condition_if_needed(attribute, serialize_method, 'this.', lines, False, False)

    def _serialize_attribute_flags(self, attribute, serialize_method):
        size = get_attribute_size(self.schema, attribute)
        method = '{0}(this.{1}(), {2})'.format(get_read_method_name(size),
                                               self._get_generated_getter_name(attribute['name']),
                                               size) if size < 8 else '{0}(this.{1}())'.format(get_read_method_name(size),
                                                                                               self._get_generated_getter_name(
                                                                                                   attribute['name']))
        lines = ['const {0}Bytes = {1}'.format(attribute['name'], method)]
        lines += ['newArray = GeneratorUtils.concatTypedArrays(newArray, {0})'.format(attribute['name']+'Bytes')]
        self._add_attribute_condition_if_needed(attribute, serialize_method, 'this.', lines, False, False)

    def _generate_serialize_attributes(self, attribute, serialize_method):
        attribute_name = attribute['name']
        attribute_bytes_name = self._get_serialize_name(attribute_name)
        if self.is_count_size_field(attribute):
            size = get_attribute_size(self.schema, attribute)
            size_extension = '.length'
            attribute_name = get_attribute_if_size(attribute['name'], self.class_schema['layout'], self.schema)
            full_property_name = 'this.{0}'.format(attribute_name + size_extension)
            if attribute['name'] == 'payloadSize' and self.name == 'AggregateTransactionBody':
                full_property_name = 'EmbeddedTransactionHelper.getEmbeddedTransactionSize(this.{0})'.format(attribute_name)
            method = '{0}({1}, {2})'.format(get_read_method_name(size), full_property_name, size)
            if size == 8:
                method = '{0}(GeneratorUtils.fromUint({1}))'.format(get_read_method_name(size), full_property_name)
            line = 'const {0} = {1}'.format(attribute_bytes_name, method)
            line2 = 'newArray = GeneratorUtils.concatTypedArrays(newArray, {0})'.format(attribute_bytes_name)
            serialize_method.add_instructions([line])
            serialize_method.add_instructions([line2])
        else:
            serialize_attribute = {
                AttributeType.SIMPLE: self._serialize_attribute_simple,
                AttributeType.BUFFER: self._serialize_attribute_buffer,
                AttributeType.ARRAY: self._serialize_attribute_array,
                AttributeType.CUSTOM: self._serialize_attribute_custom,
                AttributeType.FLAGS: self._serialize_attribute_flags,
                AttributeType.SIZE_FIELD: self._serialize_attribute_size_field,
                AttributeType.FILL_ARRAY: self._serialize_attribute_array,
                AttributeType.VAR_ARRAY: self._serialize_attribute_array
            }

            attribute_kind = get_real_attribute_type(attribute)
            serialize_attribute[attribute_kind](attribute, serialize_method)

    def _serialize_attribute_size_field(self, attribute, serialize_method):
        attribute_name = attribute['name']
        size = get_attribute_size(self.schema, attribute)
        parent_attribute = get_attribute_property_equal(self.schema, self.class_schema['layout'], 'size', attribute['name'])
        if parent_attribute is not None and is_var_array(parent_attribute):
            size_statement = self._get_size_statement(parent_attribute)
            print('get size update', size_statement, attribute)
        else:
            size_extension = '.size()' if attribute_name.endswith('Count') else '.array().length'
            # pylint: disable=unused-variable
            full_property_name = '({0}) {1}'.format(get_builtin_type(size), 'this.' +
                                                    get_attribute_if_size(attribute['name'], self.class_schema['layout'],
                                                                          self.schema) + size_extension)
        line = 'dataOutputStream.{0}({1})'
        serialize_method.add_instructions([line])

    def _get_size_statement(self, attribute):
        kind = get_real_attribute_type(attribute)

        if kind == AttributeType.SIMPLE:
            return '{0}; // {1}'.format(attribute['size'], attribute['name'])
        if kind == AttributeType.BUFFER:
            return 'this.{0}.array().length;'.format(attribute['name'])
        if is_array(kind):
            return 'this.{0}.stream().mapToInt(o -> o.getSize()).sum();'.format(attribute['name'])
        if kind == AttributeType.FLAGS:
            return '{0}.values()[0].getSize(); // {1}'.format(get_generated_class_name(attribute['type'], attribute, self.schema),
                                                              attribute['name'])
        if kind == AttributeType.SIZE_FIELD:
            return '{0}; // {1}'.format(attribute['size'], attribute['name'])
        return 'this.{0}.getSize();'.format(attribute['name'])

    def _add_getters_field(self):
        self._recursive_attribute_iterator(
            self.name, self._add_getters, self.schema, [self.base_class_name])

    def _create_public_declarations(self):
        if self.conditional_param_list:
            self._add_constructors()
            # self._add_factory_methods()
        else:
            self._add_constructor()
            # self._add_factory_method()

    def _add_load_from_binary_custom(self, load_from_binary_method):
        if self.base_class_name is not None:
            lines = ['const superObject = {0}.loadFromBinary(Uint8Array.from(byteArray))'
                     .format(get_generated_class_name(self.base_class_name, self.schema[self.base_class_name], self.schema))]
            lines += ['byteArray.splice(0, superObject.getSize())']
            load_from_binary_method.add_instructions(lines)

        self._recursive_attribute_iterator(self.name, self._generate_load_from_binary_attributes,
                                           load_from_binary_method, [self.base_class_name, self._get_body_class_name()])

        for line in self._load_from_binary_condition_lines:
            load_from_binary_method.add_instructions([line], False)

        load_from_binary_method.add_instructions(['return new {0}({1})'.format(self.generated_class_name,
                                                                               ', '.join(self.load_from_binary_atrribute_list))])

    def _add_serialize_custom(self, serialize_method):
        if self.base_class_name is not None:
            serialize_method.add_instructions(['const superBytes = super.serialize()'])
            serialize_method.add_instructions(['newArray = GeneratorUtils.concatTypedArrays(newArray, superBytes)'])
        self._recursive_attribute_iterator(self.name, self._generate_serialize_attributes,
                                           serialize_method, [self.base_class_name, self._get_body_class_name()])

    def _add_to_variable_list(self, attribute, context):
        param_list, condition_attribute = context
        name = attribute['name']
        if self._should_declaration(attribute) and self._should_add_base_on_condition(attribute, condition_attribute) and \
                not is_reserved_field(attribute):
            param_list.append(name)

    def _add_to_param(self, attribute, context):
        param_list, condition_attribute_list = context
        if self._should_declaration(attribute) and self._should_add_base_on_condition(attribute, condition_attribute_list) and \
                not is_reserved_field(attribute):
            is_condition_attribute = self._is_attribute_conditional(attribute, condition_attribute_list)
            attribute_name = attribute['name']
            attribute_type = get_generated_type(self.schema, attribute)
            if attribute_type not in ['number', 'Uint8Array']:
                self._add_required_import(format_import(attribute_type))
            param = '{1}{2}: {0}'.format(attribute_type,
                                         attribute_name, '?' if is_condition_attribute else '')
            if is_condition_attribute:
                self.condition_param.append(param)
            else:
                param_list.append(param)

    def _create_list(self, name, callback, condition_attribute_list):
        param_list = []
        self._recursive_attribute_iterator(name, callback, (param_list, condition_attribute_list), [])
        if not param_list and not self.condition_param:
            return ''
        param_string = param_list[0] if param_list else self.condition_param[0]
        for param in param_list[1:]:
            param_string += ', {0}'.format(param)

        for condition_param in self.condition_param if param_list else self.condition_param[1:]:
            param_string += ', {0}'.format(condition_param)

        self.condition_param = []
        return param_string

    @staticmethod
    def _reorder_condition_attribute_if_needed(original_list, condition_attribute_list):
        ordered_list = original_list
        if condition_attribute_list:
            condition_vars = list(map(lambda x: x['name'], condition_attribute_list))
            if set(condition_vars).issubset(set(original_list)):
                condition_list = [x for x in original_list if x not in condition_vars]
                condition_list.extend(condition_vars)
                ordered_list = condition_list
        return ordered_list

    def _create_custom_variable_list(self, name, callback, condition_attribute_list, object_name):
        param_list = []
        self._recursive_attribute_iterator(name, callback, (param_list, condition_attribute_list), [])
        param_list = self._reorder_condition_attribute_if_needed(param_list, condition_attribute_list)
        if not param_list:
            return ''
        param_string = object_name + '.' + param_list[0]
        for param in param_list[1:]:
            param_string += ', {0}'.format(object_name + '.' + param)
        return param_string

    def _create_param_list(self, condition_attribute_list):
        return self._create_list(self.name, self._add_to_param, condition_attribute_list)

    def _add_name_comment(self, attribute, context):
        comment_list, condition_attribute_list = context
        if self._should_declaration(attribute) and self._should_add_base_on_condition(attribute, condition_attribute_list) and \
                not is_reserved_field(attribute):
            comment_list.append((attribute['name'], get_comments_from_attribute(attribute, False)))

    def _create_name_comment_list(self, name, condition_variable):
        name_comment_list = []
        self._recursive_attribute_iterator(name, self._add_name_comment, (name_comment_list, condition_variable), [])
        return name_comment_list

    def _add_attribute_to_list(self, attribute, context):
        attribute_list, condition_attribute_list = context
        if self._should_add_base_on_condition(attribute, condition_attribute_list):
            attribute_list.append(attribute)

    def _add_constructor(self):
        self._add_constructor_internal(None)

    def _get_inline_method_factory(self, variable, condition_attribute_list):
        if condition_attribute_list:
            condition_vars = list(map(lambda x: x['name'], condition_attribute_list))
            var_list = [x for x in self._create_list(variable['type'], self._add_to_variable_list,
                                                     condition_attribute_list).split(', ') if x not in condition_vars]
            var_list.extend(condition_vars)
            return 'this.{0} = new {1}({2})'.format(variable['name'],
                                                    get_generated_class_name(variable['type'], variable, self.schema),
                                                    ', '.join(var_list)
                                                    )
        return 'this.{0} = new {1}({2})'.format(variable['name'],
                                                get_generated_class_name(variable['type'], variable, self.schema),
                                                self._create_list(variable['type'],
                                                                  self._add_to_variable_list,
                                                                  condition_attribute_list))

    def _add_constructor_internal(self, condition_attribute_list):
        constructor_method = TypescriptMethodGenerator('public', '', 'constructor',
                                                       [self._create_param_list(condition_attribute_list)], None)
        if self.base_class_name is not None:
            constructor_method.add_instructions(
                ['super({0})'.format(self._create_list(self.base_class_name, self._add_to_variable_list, condition_attribute_list))])
            self.load_from_binary_atrribute_list.append(
                self._create_custom_variable_list(self.base_class_name, self._add_to_variable_list, condition_attribute_list,
                                                  'superObject'))

        object_attributes = []
        self._recursive_attribute_iterator(self.name, self._add_attribute_to_list, (object_attributes, condition_attribute_list),
                                           [self.base_class_name, self._get_body_class_name()])

        for variable in object_attributes:
            if self._should_declaration(variable):
                if self._is_inline_class(variable):
                    constructor_method.add_instructions(
                        [self._get_inline_method_factory(variable, condition_attribute_list)])
                    self.load_from_binary_atrribute_list.append(self._create_custom_variable_list(variable['type'],
                                                                                                  self._add_to_variable_list,
                                                                                                  condition_attribute_list,
                                                                                                  variable['name']))
                    self._add_required_import(format_import(get_generated_class_name(variable['type'], variable, self.schema)))
                elif is_reserved_field(variable):
                    constructor_method.add_instructions(['this.{0} = {1}'.format(variable['name'], get_default_value(variable))])
                else:
                    constructor_method.add_instructions(['this.{0} = {0}'.format(variable['name'])])
                    self.load_from_binary_atrribute_list.append(variable['name'])

        self.load_from_binary_atrribute_list = self._reorder_condition_attribute_if_needed(self.load_from_binary_atrribute_list,
                                                                                           condition_attribute_list)

        self._add_method_documentation(constructor_method, 'Constructor.',
                                       self._create_name_comment_list(self.name, condition_attribute_list), None)

        self._add_constructor_internal_conditional_assigments(constructor_method, condition_attribute_list)
        self._add_method(constructor_method)

    def _add_factory_method_(self):
        self._add_factory_method_internal(None)

    def _add_constructor_internal_conditional_assigments(self, constructor_method, condition_attribute_list):
        if condition_attribute_list:
            condition_attribute_list = [x for x in condition_attribute_list if x['condition_operation'] == 'equals']
            for condition_attribute in condition_attribute_list:
                condition_type_attribute = get_attribute_property_equal(self.schema, self.class_schema['layout'], 'name',
                                                                        condition_attribute['condition'], False)
                if condition_type_attribute:
                    self._add_required_import(format_import(get_generated_class_name(condition_type_attribute['type'],
                                                                                     condition_type_attribute, self.schema)))
                    condition_type_value = '{0}.{1}'.format(
                        get_generated_class_name(condition_type_attribute['type'], condition_type_attribute, self.schema),
                        create_enum_name(condition_attribute['condition_value']))
                    if condition_attribute_list[0] == condition_attribute:
                        constructor_method.add_instructions(['if ({0}) {{'.format(condition_attribute['name'])], False)
                    elif condition_attribute_list[-1] != condition_attribute:
                        constructor_method.add_instructions(['else if ({0}) {{'.format(condition_attribute['name'])], False)
                    else:
                        constructor_method.add_instructions(['else {'], False)
                    constructor_method.add_instructions([indent('this.{0} = {1}'.format(condition_attribute['condition'],
                                                                                        condition_type_value))])
                    constructor_method.add_instructions(['}'], False)
                    constructor_method.add_instructions([])

    def _add_factory_method_internal(self, condition_attribute):
        factory = TypescriptMethodGenerator('public', self.generated_class_name, 'create',
                                            [self._create_param_list(condition_attribute)], '',
                                            True)
        factory.add_instructions(['return new {0}({1})'.format(
            self.generated_class_name, self._create_list(self.name, self._add_to_variable_list, condition_attribute))])
        self._add_method_documentation(factory, 'Creates an instance of {0}.'.format(self.generated_class_name),
                                       self._create_name_comment_list(self.name, condition_attribute),
                                       'Instance of {0}.'.format(self.generated_class_name))
        self._add_method(factory)

    def _get_condition_factory_method_param(self, condition_attribute, condition_attribute_list):
        param_list = [p for p in self._create_param_list(condition_attribute_list).split(',')
                      if condition_attribute['name'] in p or '?' not in p]
        return ','.join(param_list).replace('?', '')

    def _get_condition_factory_method_impl(self, condition_attribute, condition_attribute_list):
        condition_vars = list(map(lambda x: x['name'], condition_attribute_list))
        var_list = [x for x in self._create_list(self.name, self._add_to_variable_list,
                                                 condition_attribute_list).split(', ') if x not in condition_vars]
        var_list.extend(['undefined' if x != condition_attribute['name'] else x for x in condition_vars])
        return ', '.join(var_list)

    def _add_factory_method_condition(self, condition_attribute_list):
        if condition_attribute_list:
            for condition_attribute in condition_attribute_list:
                # other_condition_vars = [x for x in condition_vars if condition_attribute['name'] not in x]

                factory = TypescriptMethodGenerator('public', self.generated_class_name,
                                                    self._get_condition_factory_method_name(condition_attribute),
                                                    [self._get_condition_factory_method_param(condition_attribute,
                                                                                              condition_attribute_list)],
                                                    '',
                                                    True)
                factory.add_instructions(['return new {0}({1})'.format(
                    self.generated_class_name, self._get_condition_factory_method_impl(condition_attribute,
                                                                                       condition_attribute_list))])
                self._add_method_documentation(factory, 'Creates an instance of {0}.'.format(self.generated_class_name),
                                               self._create_name_comment_list(self.name, condition_attribute_list),
                                               'Instance of {0}.'.format(self.generated_class_name))
                self._add_method(factory)

    def _add_constructors(self):
        self._add_constructor_internal(self.conditional_param_list)

    def _add_factory_methods(self):
        self._add_factory_method_condition(self.conditional_param_list)
