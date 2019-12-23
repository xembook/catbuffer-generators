from .Helpers import create_enum_name, get_default_value, get_class_type_from_name, get_comment_from_name, is_attribute_count_size_field
from .Helpers import get_attribute_kind, TypeDescriptorDisposition, get_attribute_if_size, is_fill_array_type
from .Helpers import get_generated_class_name, get_builtin_type, indent, get_attribute_size, is_reserved_field
from .Helpers import get_generated_type, get_attribute_property_equal, AttributeKind, is_byte_type
from .Helpers import get_read_method_name, get_reverse_method_name, get_write_method_name, is_any_array_kind, InterfaceType
from .Helpers import is_builtin_type, get_comments_from_attribute, get_import_for_type, is_var_array_type
from .JavaGeneratorBase import JavaGeneratorBase
from .JavaMethodGenerator import JavaMethodGenerator


def capitalize_first_character(string):
    return string[0].upper() + string[1:]


class JavaClassGenerator(JavaGeneratorBase):
    """Java class generator"""

    def __init__(self, name, schema, class_schema, enum_list):
        super(JavaClassGenerator, self).__init__(name, schema, class_schema)

        self.enum_list = enum_list
        self.class_type = 'class'
        self.condition_list = []
        self.condition_binary_declare_map = {}
        self.implements_list.add(InterfaceType.Serializer)

        if 'layout' in self.class_schema:
            # Find base class
            self._foreach_attributes(
                self.class_schema['layout'], self._find_base_callback)
            # Find any condition variables
            self._recurse_foreach_attribute(
                self.name, self._create_condition_list, self.condition_list, [])

    @staticmethod
    def _is_inline_class(attribute):
        return 'disposition' in attribute and attribute['disposition'] == TypeDescriptorDisposition.Inline.value

    def _find_base_callback(self, attribute):
        if self._is_inline_class(attribute) and self.should_generate_class(attribute['type']):
            self.base_class_name = attribute['type']
            self.finalized_class = True
            return True
        return False

    @staticmethod
    def _is_conditional_attribute(attribute):
        return 'condition' in attribute

    def _create_condition_list(self, attribute, condition_list):
        if self._is_conditional_attribute(attribute):
            condition_list.append(attribute)
            self.condition_binary_declare_map[attribute['condition']] = False

    def _should_declaration(self, attribute):
        return not self.is_count_size_field(attribute) and attribute['name'] != 'size'

    def _get_body_class_name(self):
        body_name = self.name if not self.name.startswith('Embedded') else self.name[8:]
        if self.name.startswith('Aggregate') and self.name.endswith('Transaction'):
            body_name = 'AggregateTransaction'
        return '{0}Body'.format(body_name)

    def _add_private_declarations(self):
        self._recurse_foreach_attribute(self.name, self._add_private_declaration, self.class_output,
                                        [self.base_class_name, self._get_body_class_name()])
        self.class_output += ['']

    def _add_required_import_if_needed(self, var_type):
        import_string = get_import_for_type(var_type)
        if import_string:
            self._add_required_import(import_string)

    def _add_private_declaration(self, attribute, private_output):
        if not self.is_count_size_field(attribute):
            line = get_comments_from_attribute(attribute)
            if line is not None:
                private_output += [indent(line)]
            attribute_name = attribute['name']
            var_type = get_generated_type(self.schema, attribute)
            self._add_required_import_if_needed(var_type)
            scope = 'private final' if (attribute_name != 'size' and not self._is_conditional_attribute(attribute)) else 'private'
            private_output += [indent('{0} {1} {2};'.format(scope, var_type, attribute_name))]

    @staticmethod
    def _get_generated_getter_name(attribute_name):
        return 'get{0}'.format(capitalize_first_character(attribute_name))

    @staticmethod
    def _add_simple_getter(attribute, new_getter):
        new_getter.add_instructions(
            ['return this.{0}'.format(attribute['name'])])

    @staticmethod
    def _add_buffer_getter(attribute, new_getter):
        new_getter.add_instructions(
            ['return this.{0}'.format(attribute['name'])])

    # pylint: disable-msg=too-many-arguments
    def _add_if_condition_for_variable_if_needed(self, attribute, writer, object_prefix, if_condition, code_lines, add_semicolon=True):
        condition_type_attribute = get_attribute_property_equal(self.schema, self.class_schema['layout'], 'name', attribute['condition'])
        condition_type = '{0}.{1}'.format(get_generated_class_name(condition_type_attribute['type'], condition_type_attribute, self.schema),
                                          create_enum_name(attribute['condition_value']))

        writer.add_instructions(['if ({0}{1} {2} {3}) {{'.format(object_prefix, attribute['condition'], if_condition, condition_type)],
                                False)
        for line in code_lines:
            writer.add_instructions([indent(line)], add_semicolon)
        writer.add_instructions(['}'], False)

    def _add_method_condition(self, attribute, method_writer):
        if 'condition' in attribute:
            code_lines = ['throw new java.lang.IllegalStateException("{0} is not set to {1}.")'.format(
                attribute['condition'], create_enum_name(attribute['condition_value']))]
            self._add_if_condition_for_variable_if_needed(attribute, method_writer, 'this.', '!=', code_lines)

    def _add_getter(self, attribute, schema):
        attribute_name = attribute['name']
        return_type = get_generated_type(schema, attribute)
        self._add_required_import_if_needed(return_type)
        scope = 'private' if is_reserved_field(attribute) else 'public'
        new_getter = JavaMethodGenerator(scope, return_type, self._get_generated_getter_name(attribute_name), [])

        if 'aggregate_class' in attribute:
            if is_reserved_field(attribute):
                return
            # This is just a pass through
            new_getter.add_instructions(
                ['return this.{0}.{1}()'.format(self._get_name_from_type(attribute['aggregate_class']),
                                                self._get_generated_getter_name(attribute_name))])
        else:
            self._add_method_condition(attribute, new_getter)
            getters = {
                AttributeKind.SIMPLE: self._add_simple_getter,
                AttributeKind.BUFFER: self._add_buffer_getter,
                AttributeKind.ARRAY: self._add_simple_getter,
                AttributeKind.CUSTOM: self._add_simple_getter,
                AttributeKind.FLAGS: self._add_simple_getter,
                AttributeKind.FILL_ARRAY: self._add_simple_getter,
                AttributeKind.VAR_ARRAY: self._add_simple_getter
            }
            attribute_kind = get_attribute_kind(attribute)
            getters[attribute_kind](attribute, new_getter)

        # If the comments is empty then just use name in the description
        description = get_comments_from_attribute(attribute, False)
        self._add_method_documentation(new_getter, 'Gets {0}.'.format(description), [], description)
        self._add_method(new_getter)

    @staticmethod
    def _add_simple_setter(attribute, new_setter):
        new_setter.add_instructions(['this.{0} = {0}'.format(attribute['name'])])

    @staticmethod
    def _add_array_setter(attribute, new_setter):
        new_setter.add_instructions(['this.{0} = {0}'.format(attribute['name'])])

    def _add_buffer_setter(self, attribute, new_setter):
        attribute_size = get_attribute_size(self.schema, attribute)
        attribute_name = attribute['name']
        new_setter.add_instructions(['GeneratorUtils.notNull({0}, "{0} is null")'.format(attribute_name)])

        if not isinstance(attribute_size, str):
            new_setter.add_instructions(
                ['GeneratorUtils.isTrue({0}.array().length == {1}, "{0} should be {1} bytes")'.format(attribute_name, attribute_size)])
        new_setter.add_instructions(['this.{0} = {0}'.format(attribute_name)])

    def _get_size_statement(self, attribute):
        kind = get_attribute_kind(attribute)

        if kind == AttributeKind.SIMPLE:
            return '{0}; // {1}'.format(attribute['size'], attribute['name'])
        if kind == AttributeKind.BUFFER:
            return 'this.{0}.array().length;'.format(attribute['name'])
        if is_any_array_kind(kind):
            return 'this.{0}.stream().mapToInt(o -> o.getSize()).sum();'.format(attribute['name'])
        if kind == AttributeKind.FLAGS:
            return '{0}.values()[0].getSize(); // {1}'.format(get_generated_class_name(attribute['type'], attribute, self.schema),
                                                              attribute['name'])
        if kind == AttributeKind.SIZE_FIELD:
            return '{0}; // {1}'.format(attribute['size'], attribute['name'])

        return 'this.{0}.getSize();'.format(attribute['name'])

    def _add_size_value(self, attribute, method_writer):
        line = 'size += ' + self._get_size_statement(attribute)
        self._add_attribute_condition_if_needed(attribute, method_writer, 'this.', [line], False)

    def _calculate_size(self, new_getter):
        return_type = 'int'
        if self.base_class_name is not None:
            new_getter.add_instructions(['{0} size = super.getSize()'.format(return_type)])
        else:
            new_getter.add_instructions(['{0} size = 0'.format(return_type)])
        self._recurse_foreach_attribute(self.name, self._add_size_value, new_getter, [self.base_class_name, self._get_body_class_name()])
        new_getter.add_instructions(['return size'])

    def _add_body_getter(self):
        if self.base_class_name in ['Transaction', 'EmbeddedTransaction']:
            body_class_name = self._get_body_class_name()
            new_getter = JavaMethodGenerator('public', body_class_name + 'Builder', 'getBody', [])
            new_getter.add_annotation('@Override')
            new_getter.add_instructions(['return this.' + body_class_name[0].lower() + body_class_name[1:]])
            self._add_method_documentation(new_getter, 'Gets the body builder of the object.', [], 'Body builder.')
            self._add_method(new_getter)
        elif self.name in ['Transaction', 'EmbeddedTransaction']:
            body_class_name = self._get_body_class_name()
            new_getter = JavaMethodGenerator('public', 'Serializer', 'getBody', [])
            new_getter.add_instructions(['return null'])
            self._add_method_documentation(new_getter, 'Gets the body builder of the object.', [], 'Body builder.')
            self._add_method(new_getter)

    def _add_stream_size_getter(self):
        new_getter = JavaMethodGenerator('public', 'int', 'getStreamSize', [])
        new_getter.add_instructions(['return this.size'])
        self._add_method_documentation(new_getter, 'Gets the size if created from a stream otherwise zero', [], 'Object size from stream')
        self._add_method(new_getter)

    def _add_getters(self, attribute, schema):
        if self._should_declaration(attribute):
            self._add_getter(attribute, schema)
        elif attribute['name'] == 'size':
            self._add_stream_size_getter()

    @staticmethod
    def _get_name_from_type(type_name):
        return type_name[0].lower() + type_name[1:]

    def _recurse_foreach_attribute(self, class_name, callback, context, ignore_inline_class):
        class_generated = (class_name != self.name and self.should_generate_class(class_name))
        for attribute in self.schema[class_name]['layout']:
            if class_generated:
                attribute['aggregate_class'] = class_name

            if 'disposition' in attribute:
                inline_class = attribute['type']
                if attribute['disposition'] == TypeDescriptorDisposition.Inline.value:
                    if self.should_generate_class(inline_class):
                        # Class was generated so it can be declare aggregate
                        attribute['name'] = self._get_name_from_type(inline_class)
                        if (self.base_class_name == inline_class and
                                self.base_class_name in ignore_inline_class):
                            continue  # skip the base class
                        if inline_class in ignore_inline_class:
                            callback(attribute, context)
                            continue

                    self._recurse_foreach_attribute(inline_class, callback, context, ignore_inline_class)
                elif attribute['disposition'] == TypeDescriptorDisposition.Const.value:
                    # add dynamic enum if present in this class
                    enum_name = attribute['type']
                    if enum_name in self.enum_list:
                        self.enum_list[enum_name].add_enum_value(self.generated_class_name, attribute['value'],
                                                                 get_comment_from_name(self.generated_class_name))
                    continue
                elif is_var_array_type(attribute) or is_fill_array_type(attribute):
                    callback(attribute, context)
                    continue
            else:
                callback(attribute, context)

    def _init_other_attribute_in_condition(self, attribute, obj_prefix, code_lines):
        if self._is_conditional_attribute(attribute):
            for condition_attribute in self.condition_list:
                if attribute['name'] != condition_attribute['name']:
                    code_lines.append('{0}{1} = {2}'.format(obj_prefix, condition_attribute['name'], get_default_value(attribute)))

    def _add_attribute_condition_if_needed(self, attribute, method_writer, obj_prefix, code_lines, add_semicolon=True):
        if self._is_conditional_attribute(attribute):
            self._add_if_condition_for_variable_if_needed(attribute, method_writer, obj_prefix, '==', code_lines, add_semicolon)
        else:
            method_writer.add_instructions(code_lines, add_semicolon)

    @staticmethod
    def _get_condition_local_variable_name(attribute):
        return attribute['condition'] + 'Condition'

    def _is_use_in_condition(self, attribute, method_writer, prefix):
        if 'layout' not in self.class_schema:
            return
        condition_attribute = get_attribute_property_equal(self.schema, self.class_schema['layout'], 'condition', attribute['name'])
        if condition_attribute is None:
            return
        for condition_attribute in self.condition_list:
            if attribute['name'] == condition_attribute['condition']:
                lines = ['{0}{1} = new {2}({3})'.format(prefix, condition_attribute['name'],
                                                        get_generated_class_name(condition_attribute['type'], self.class_schema,
                                                                                 self.schema),
                                                        self._get_condition_local_variable_name(condition_attribute))]
                self._init_other_attribute_in_condition(condition_attribute, prefix, lines)
                self._add_attribute_condition_if_needed(condition_attribute, method_writer, prefix, lines)

    def _add_simple_load_from_binary_for_condition_variable(self, attribute, load_from_binary_method):
        if self.condition_binary_declare_map[attribute['condition']]:
            return
        size = get_attribute_size(self.schema, attribute)
        read_method_name = 'stream.{0}()'.format(get_read_method_name(size))
        reverse_byte_method = get_reverse_method_name(size).format(read_method_name)
        load_from_binary_method.add_instructions(
            ['final {0} {1} = {2}'.format(get_builtin_type(size), self._get_condition_local_variable_name(attribute), reverse_byte_method)])
        self.condition_binary_declare_map[attribute['condition']] = True

    def _load_from_binary_simple(self, attribute, load_from_binary_method):
        size = get_attribute_size(self.schema, attribute)
        read_method_name = 'stream.{0}()'.format(get_read_method_name(size))
        reverse_byte_method = get_reverse_method_name(size).format(read_method_name)
        load_from_binary_method.add_instructions(['this.{0} = {1}'.format(attribute['name'], reverse_byte_method)])
        self._is_use_in_condition(attribute, load_from_binary_method, 'this.')

    def _load_from_binary_buffer(self, attribute, load_from_binary_method):
        attribute_name = attribute['name']
        attribute_size = get_attribute_size(self.schema, attribute)
        load_from_binary_method.add_instructions(['this.{0} = ByteBuffer.allocate({1})'.format(attribute_name, attribute_size)])
        load_from_binary_method.add_instructions(
            ['stream.{0}(this.{1}.array())'.format(get_read_method_name(attribute_size), attribute_name)])

    def _load_from_binary_array(self, attribute, load_from_binary_method):
        attribute_typename = attribute['type']
        attribute_sizename = attribute['size']
        attribute_name = attribute['name']
        load_from_binary_method.add_instructions(['this.{0} = new java.util.ArrayList<>({1})'.format(attribute_name, attribute_sizename)])
        load_from_binary_method.add_instructions(['for (int i = 0; i < {0}; i++) {{'.format(attribute_sizename)], False)

        if is_byte_type(attribute_typename):
            load_from_binary_method.add_instructions([indent('{0}.add(stream.{1}())'.format(attribute_name, get_read_method_name(1)))])
        else:
            load_from_binary_method.add_instructions(
                [indent('{0}.add({1}.loadFromBinary(stream))'.format(attribute_name, get_generated_class_name(attribute_typename, attribute,
                                                                                                              self.schema)))])
        load_from_binary_method.add_instructions(['}'], False)

    def _load_from_binary_fill_array(self, attribute, load_from_binary_method):
        attribute_typename = attribute['type']
        attribute_name = attribute['name']
        load_from_binary_method.add_instructions(['this.{0} = new java.util.ArrayList<>()'.format(attribute_name)])
        load_from_binary_method.add_instructions(['while (stream.available() > 0) {'], False)

        if is_byte_type(attribute_typename):
            load_from_binary_method.add_instructions([indent('{0}.add(stream.{1}())'.format(attribute_name, get_read_method_name(1)))])
        else:
            load_from_binary_method.add_instructions(
                [indent('{0}.add({1}.loadFromBinary(stream))'.format(attribute_name, get_generated_class_name(attribute_typename, attribute,
                                                                                                              self.schema)))])
        load_from_binary_method.add_instructions(['}'], False)

    def _load_from_binary_var_array(self, attribute, load_from_binary_method):
        attribute_typename = attribute['type']
        attribute_sizename = attribute['size']
        attribute_name = attribute['name']
        load_from_binary_method.add_instructions(
            ['final ByteBuffer transactionBytes = ByteBuffer.allocate({0})'.format(attribute_sizename)])
        self._add_required_import_if_needed('ByteBuffer')
        load_from_binary_method.add_instructions(['stream.read(transactionBytes.array())'])
        load_from_binary_method.add_instructions(
            ['final DataInputStream dataInputStream =  new DataInputStream(new ByteArrayInputStream(transactionBytes.array()))'])
        self._add_required_import_if_needed('ByteArrayInputStream')
        load_from_binary_method.add_instructions(['this.{0} = new java.util.ArrayList<>()'.format(attribute_name)])
        load_from_binary_method.add_instructions(['while (dataInputStream.available() > 0) {'], False)

        if is_byte_type(attribute_typename):
            load_from_binary_method.add_instructions(
                [indent('{0}.add(dataInputStream.{1}())'.format(attribute_name, get_read_method_name(1)))])
        else:
            load_from_binary_method.add_instructions(
                [indent('{0}.add({1}.loadFromBinary(dataInputStream))'.format(attribute_name,
                                                                              get_generated_class_name(attribute_typename, attribute,
                                                                                                       self.schema)))])
        load_from_binary_method.add_instructions(['}'], False)

    def _load_from_binary_custom(self, attribute, load_from_binary_method):
        if self._is_conditional_attribute(attribute):
            self._add_simple_load_from_binary_for_condition_variable(attribute, load_from_binary_method)
            return

        lines = ['this.{0} = {1}.loadFromBinary(stream)'.format(attribute['name'],
                                                                get_generated_class_name(attribute['type'], attribute, self.schema))]
        load_from_binary_method.add_instructions(lines)
        self._is_use_in_condition(attribute, load_from_binary_method, 'this.')

    def _load_from_binary_flags(self, attribute, load_from_binary_method):
        size = get_attribute_size(self.schema, attribute)
        read_method_name = 'stream.{0}()'.format(get_read_method_name(size))
        reverse_byte_method = get_reverse_method_name(size).format(read_method_name)
        lines = ['this.{0} = GeneratorUtils.toSet({1}, {2})'.format(attribute['name'],
                                                                    get_class_type_from_name(
                                                                        get_generated_class_name(attribute['type'], attribute,
                                                                                                 self.schema)),
                                                                    reverse_byte_method)]
        load_from_binary_method.add_instructions(lines)
        self._is_use_in_condition(attribute, load_from_binary_method, 'this.')

    def _load_from_binary_field(self, attribute, load_from_binary_method):
        attribute_name = attribute['name']
        read_method_name = 'stream.{0}()'.format(get_read_method_name(attribute['size']))
        size = get_attribute_size(self.schema, attribute)
        reverse_byte_method = get_reverse_method_name(size).format(read_method_name)
        load_from_binary_method.add_instructions(
            ['final {0} {1} = {2}'.format(get_generated_type(self.schema, attribute), attribute_name, reverse_byte_method)])

    @staticmethod
    def is_count_size_field(field):
        return is_attribute_count_size_field(field)

    def _generate_load_from_binary_attributes(self, attribute, load_from_binary_method):
        load_attribute = {
            AttributeKind.SIMPLE: self._load_from_binary_simple,
            AttributeKind.BUFFER: self._load_from_binary_buffer,
            AttributeKind.ARRAY: self._load_from_binary_array,
            AttributeKind.CUSTOM: self._load_from_binary_custom,
            AttributeKind.FLAGS: self._load_from_binary_flags,
            AttributeKind.SIZE_FIELD: self._load_from_binary_field,
            AttributeKind.FILL_ARRAY: self._load_from_binary_fill_array,
            AttributeKind.VAR_ARRAY: self._load_from_binary_var_array
        }

        attribute_kind = get_attribute_kind(attribute)
        load_attribute[attribute_kind](attribute, load_from_binary_method)

    def _serialize_attribute_simple(self, attribute, serialize_method):
        size = get_attribute_size(self.schema, attribute)
        reverse_byte_method = get_reverse_method_name(size).format('this.' + self._get_generated_getter_name(attribute['name'] + '()'))
        line = 'dataOutputStream.{0}({1})'.format(get_write_method_name(size), reverse_byte_method)
        self._add_attribute_condition_if_needed(attribute, serialize_method, 'this.', [line])

    def _serialize_attribute_buffer(self, attribute, serialize_method):
        attribute_name = attribute['name']
        attribute_size = get_attribute_size(self.schema, attribute)
        serialize_method.add_instructions(['dataOutputStream.{0}(this.{1}.array(), 0, this.{1}.array().length)'.format(
            get_write_method_name(attribute_size), attribute_name)])

    @staticmethod
    def _get_serialize_name(attribute_name):
        return '{0}Bytes'.format(attribute_name)

    def _serialize_attribute_array(self, attribute, serialize_method):
        attribute_typename = attribute['type']
        attribute_size = attribute['size']
        attribute_name = attribute['name']
        serialize_method.add_instructions(['for (int i = 0; i < this.{0}.size(); i++) {{'.format(attribute_name)], False)

        if is_byte_type(attribute_typename):
            serialize_method.add_instructions(
                [indent('dataOutputStream.{0}(this.{1}.get(i))'.format(get_write_method_name(1), attribute_name))])
        else:
            attribute_bytes_name = self._get_serialize_name(attribute_name)
            serialize_method.add_instructions(
                [indent('final byte[] {0} = this.{1}.get(i).serialize()'.format(attribute_bytes_name, attribute_name))])
            serialize_method.add_instructions(
                [indent('dataOutputStream.{0}({1}, 0, {1}.length)'.format(get_write_method_name(attribute_size), attribute_bytes_name))])
        serialize_method.add_instructions(['}'], False)

    def _serialize_attribute_custom(self, attribute, serialize_method):
        attribute_name = attribute['name']
        attribute_bytes_name = self._get_serialize_name(attribute_name)
        lines = ['final byte[] {0} = this.{1}.serialize()'.format(attribute_bytes_name, attribute_name)]
        lines += ['dataOutputStream.write({0}, 0, {0}.length)'.format(attribute_bytes_name)]
        self._add_attribute_condition_if_needed(attribute, serialize_method, 'this.', lines)

    def _serialize_attribute_flags(self, attribute, serialize_method):
        attribute_name = attribute['name']
        size = get_attribute_size(self.schema, attribute)
        enum_type = get_builtin_type(size)
        line = 'final {0} bitMask = '.format(enum_type)
        if size < 8:  # cast is required since the bitmask is a long
            line += '({0}) '.format(enum_type)
        line += 'GeneratorUtils.toLong({0}, this.{1})'.format(
            get_class_type_from_name(get_generated_class_name(attribute['type'], attribute, self.schema)),
            attribute_name)

        lines = [line]
        reverse_byte_method = get_reverse_method_name(size).format('bitMask')
        lines += ['dataOutputStream.{0}({1})'.format(get_write_method_name(size), reverse_byte_method)]
        self._add_attribute_condition_if_needed(attribute, serialize_method, 'this.', lines)

    def _serialize_attribute_size_field(self, attribute, serialize_method):
        attribute_name = attribute['name']
        size = get_attribute_size(self.schema, attribute)
        parent_attribute = get_attribute_property_equal(self.schema, self.class_schema['layout'], 'size', attribute['name'])
        if parent_attribute is not None and is_var_array_type(parent_attribute):
            size_statement = self._get_size_statement(parent_attribute)
            full_property_name = '({0}) {1}'.format(get_builtin_type(size), size_statement[:-1])
        else:
            size_extension = '.size()' if attribute_name.endswith('Count') else '.array().length'
            full_property_name = '({0}) {1}'.format(get_builtin_type(size), 'this.' +
                                                    get_attribute_if_size(attribute['name'], self.class_schema['layout'],
                                                                          self.schema) + size_extension)
        reverse_byte_method = get_reverse_method_name(size).format(full_property_name)
        line = 'dataOutputStream.{0}({1})'.format(get_write_method_name(size), reverse_byte_method)
        serialize_method.add_instructions([line])

    def _generate_serialize_attributes(self, attribute, serialize_method):
        serialize_attribute = {
            AttributeKind.SIMPLE: self._serialize_attribute_simple,
            AttributeKind.BUFFER: self._serialize_attribute_buffer,
            AttributeKind.ARRAY: self._serialize_attribute_array,
            AttributeKind.CUSTOM: self._serialize_attribute_custom,
            AttributeKind.FLAGS: self._serialize_attribute_flags,
            AttributeKind.SIZE_FIELD: self._serialize_attribute_size_field,
            AttributeKind.FILL_ARRAY: self._serialize_attribute_array,
            AttributeKind.VAR_ARRAY: self._serialize_attribute_array
        }

        attribute_kind = get_attribute_kind(attribute)
        serialize_attribute[attribute_kind](attribute, serialize_method)

    def _add_getters_field(self):
        self._recurse_foreach_attribute(
            self.name, self._add_getters, self.schema, [self.base_class_name])

    def _add_public_declarations(self):
        self._add_constructor_stream()
        if self.condition_list:
            self._add_constructors()
            self._add_factory_methods()
        else:
            self._add_constructor()
            self._add_factory_method()
        self._add_getters_field()

    def _add_load_from_binary_custom(self, load_from_binary_method):
        load_from_binary_method.add_instructions(['return new {0}(stream)'.format(self.generated_class_name)])

    def _add_serialize_custom(self, serialize_method):
        if self.base_class_name is not None:
            serialize_method.add_instructions(['final byte[] superBytes = super.serialize()'])
            serialize_method.add_instructions(['dataOutputStream.write(superBytes, 0, superBytes.length)'])
        self._recurse_foreach_attribute(self.name, self._generate_serialize_attributes,
                                        serialize_method, [self.base_class_name, self._get_body_class_name()])

    def _add_constructor_stream(self):
        load_stream_constructor = JavaMethodGenerator('protected', '', self.generated_class_name, ['final DataInputStream stream'], '')
        if self.base_class_name is not None:
            load_stream_constructor.add_instructions(['super(stream)'])
        attributes = []
        self._recurse_foreach_attribute(self.name, self._add_attribute_to_list, (attributes, None),
                                        [self.base_class_name, self._get_body_class_name()])
        wrap_code = False
        for attribute in attributes:
            attribute_kind = get_attribute_kind(attribute)
            if attribute_kind != AttributeKind.CUSTOM:
                wrap_code = True
                break
        if wrap_code:
            self.wrap_code_in_try(load_stream_constructor,
                                  lambda: self._recurse_foreach_attribute(self.name, self._generate_load_from_binary_attributes,
                                                                          load_stream_constructor,
                                                                          [self.base_class_name, self._get_body_class_name()]))
        else:
            self._recurse_foreach_attribute(self.name, self._generate_load_from_binary_attributes,
                                            load_stream_constructor,
                                            [self.base_class_name, self._get_body_class_name()])

        self._add_method_documentation(load_stream_constructor, 'Constructor - Creates an object from stream.',
                                       [('stream', 'Byte stream to use to serialize the object.')], None)
        self._add_method(load_stream_constructor)

    def _add_to_variable(self, attribute, context):
        param_list, condition_attribute = context
        attribute_name = attribute['name']
        if self._should_declaration(attribute) and self._should_add_base_on_condition(attribute, condition_attribute) and \
                not is_reserved_field(attribute):
            param_list.append(attribute_name)

    @staticmethod
    def _should_add_base_on_condition(attribute, condition_attribute):
        attribute_name = attribute['name']
        if condition_attribute is not None:
            if 'condition' in attribute:
                if condition_attribute['condition'] == attribute['condition'] and condition_attribute['name'] != attribute_name:
                    return False  # Skip all other conditions attribute
            elif condition_attribute['condition'] == attribute_name:
                return False
        return True

    def _add_to_param(self, attribute, context):
        param_list, condition_attribute = context
        if self._should_declaration(attribute) and self._should_add_base_on_condition(attribute, condition_attribute) and \
                not is_reserved_field(attribute):
            attribute_name = attribute['name']
            attribute_type = get_generated_type(self.schema, attribute)
            param_list.append('final {0} {1}'.format(attribute_type, attribute_name))

    def _create_list(self, name, callback, condition_attribute):
        param_list = []
        self._recurse_foreach_attribute(name, callback, (param_list, condition_attribute), [])
        if not param_list:
            return ''
        param_value = param_list[0]
        for param in param_list[1:]:
            param_value += ', {0}'.format(param)
        return param_value

    def _create_param_list(self, condition_attribute):
        return self._create_list(self.name, self._add_to_param, condition_attribute)

    def _add_name_comment(self, attribute, context):
        comment_list, condition_attribute = context
        if self._should_declaration(attribute) and self._should_add_base_on_condition(attribute, condition_attribute) and \
                not is_reserved_field(attribute):
            comment_list.append((attribute['name'], get_comments_from_attribute(attribute, False)))

    def _create_name_comment_list(self, name, condition_variable):
        name_comment_list = []
        self._recurse_foreach_attribute(name, self._add_name_comment, (name_comment_list, condition_variable), [])
        return name_comment_list

    def _add_attribute_to_list(self, attribute, context):
        attribute_list, condition_attribute = context
        if self._should_add_base_on_condition(attribute, condition_attribute):
            attribute_list.append(attribute)

    def _add_constructor(self):
        self._add_constructor_internal(None)

    def _add_constructor_internal(self, condition_attribute):
        constructor_method = JavaMethodGenerator('protected', '', self.generated_class_name, [self._create_param_list(condition_attribute)],
                                                 None)
        if self.base_class_name is not None:
            constructor_method.add_instructions(
                ['super({0})'.format(self._create_list(self.base_class_name, self._add_to_variable, condition_attribute))])

        object_attributes = []
        self._recurse_foreach_attribute(self.name, self._add_attribute_to_list, (object_attributes, condition_attribute),
                                        [self.base_class_name, self._get_body_class_name()])
        for attribute in object_attributes:
            if self._is_inline_class(attribute):
                continue
            if 'size' not in attribute or not is_builtin_type(attribute['type'], attribute['size']):
                constructor_method.add_instructions(['GeneratorUtils.notNull({0}, "{0} is null")'.format(attribute['name'])])

        for variable in object_attributes:
            if self._should_declaration(variable):
                if self._is_inline_class(variable):
                    constructor_method.add_instructions(
                        ['this.{0} = {1}.create({2})'.format(variable['name'],
                                                             get_generated_class_name(variable['type'], variable, self.schema),
                                                             self._create_list(variable['type'], self._add_to_variable,
                                                                               condition_attribute))])
                elif is_reserved_field(variable):
                    constructor_method.add_instructions(['this.{0} = {1}'.format(variable['name'], get_default_value(variable))])
                else:
                    constructor_method.add_instructions(['this.{0} = {0}'.format(variable['name'])])

        if condition_attribute:
            condition_type_attribute = get_attribute_property_equal(self.schema, self.class_schema['layout'], 'name',
                                                                    condition_attribute['condition'], False)
            if condition_type_attribute:
                condition_type_value = '{0}.{1}'.format(
                    get_generated_class_name(condition_type_attribute['type'], condition_type_attribute, self.schema),
                    create_enum_name(condition_attribute['condition_value']))
                constructor_method.add_instructions(['this.{0} = {1}'.format(condition_attribute['condition'], condition_type_value)])
                code_lines = []
                self._init_other_attribute_in_condition(condition_attribute, 'this.', code_lines)
                constructor_method.add_instructions(code_lines)

        self._add_method_documentation(constructor_method, 'Constructor.', self._create_name_comment_list(self.name, condition_attribute),
                                       None)
        self._add_method(constructor_method)

    def _add_factory_method(self):
        self._add_factory_method_internal(None)

    def _add_factory_method_internal(self, condition_attribute):
        factory = JavaMethodGenerator('public', self.generated_class_name, 'create', [self._create_param_list(condition_attribute)], '',
                                      True)
        factory.add_instructions(['return new {0}({1})'.format(
            self.generated_class_name, self._create_list(self.name, self._add_to_variable, condition_attribute))])
        self._add_method_documentation(factory, 'Creates an instance of {0}.'.format(self.generated_class_name),
                                       self._create_name_comment_list(self.name, condition_attribute),
                                       'Instance of {0}.'.format(self.generated_class_name))
        self._add_method(factory)

    def _add_constructors(self):
        for attribute in self.condition_list:
            self._add_constructor_internal(attribute)

    def _add_factory_methods(self):
        for attribute in self.condition_list:
            self._add_factory_method_internal(attribute)

    @staticmethod
    def should_generate_class(name):
        return ((name.startswith('Embedded') and not name.endswith('Header'))
                or name.endswith('Transaction')
                or name.startswith('Mosaic')
                or name.endswith('Mosaic')
                or name.endswith('Modification')
                or (name.endswith('Body') and name != 'EntityBody')
                or name.endswith('Cosignature'))
