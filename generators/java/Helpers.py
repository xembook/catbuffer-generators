from enum import Enum


class TypeDescriptorType(Enum):
    """Type descriptor enum"""
    Byte = 'byte'
    Struct = 'struct'
    Enum = 'enum'


class InterfaceType(Enum):
    """Interface type enum"""
    BitMaskable = 'BitMaskable'
    Serializer = 'Serializer'


def is_struct_type(typename):
    return typename == TypeDescriptorType.Struct.value


def is_enum_type(typename):
    return typename == TypeDescriptorType.Enum.value


def is_byte_type(typename):
    return typename == TypeDescriptorType.Byte.value


def is_inline_type(attribute):
    return 'disposition' in attribute and attribute['disposition'] == TypeDescriptorDisposition.Inline.value


def is_const_type(attribute):
    return 'disposition' in attribute and attribute['disposition'] == TypeDescriptorDisposition.Const.value


def is_fill_array_type(attribute):
    return 'disposition' in attribute and attribute['disposition'] == TypeDescriptorDisposition.Fill.value


def is_var_array_type(attribute):
    return 'disposition' in attribute and attribute['disposition'] == TypeDescriptorDisposition.Var.value


def is_any_array_kind(attribute_kind):
    return attribute_kind in (AttributeKind.ARRAY, AttributeKind.VAR_ARRAY, AttributeKind.FILL_ARRAY)


def is_sorted_array(attribute):
    return 'sort_key' in attribute


def is_reserved_field(attribute):
    return '_Reserved' in attribute['name']


def is_attribute_count_size_field(attribute):
    return attribute['name'].endswith('Size') or attribute['name'].endswith('Count')


def get_generated_class_name(typename, class_schema, schema):
    class_type = class_schema['type']
    default_name = typename + 'Dto'
    if is_byte_type(class_type) or is_enum_type(class_type) or typename not in schema:
        return default_name
    return typename + 'Builder' if is_struct_type(schema[typename]['type']) else default_name


def is_builtin_type(typename, size):
    # byte up to long are passed as 'byte' with size set to proper value
    return not isinstance(size, str) and is_byte_type(typename) and size <= 8


class AttributeKind(Enum):
    """Attribute type enum"""
    SIMPLE = 1
    BUFFER = 2
    ARRAY = 3
    CUSTOM = 4
    FLAGS = 5
    SIZE_FIELD = 6
    FILL_ARRAY = 7
    VAR_ARRAY = 8
    UNKNOWN = 100


def get_attribute_size(schema, attribute):
    if 'size' not in attribute and not is_byte_type(attribute['type']) and not is_enum_type(attribute['type']):
        attr = schema[attribute['type']]
        if 'size' in attr:
            return attr['size']
        return 1
    return attribute['size']


def is_flags_enum(name):
    return name.endswith('Flags')


# pylint: disable=R0911
def get_attribute_kind(attribute):
    if is_var_array_type(attribute):
        return AttributeKind.VAR_ARRAY
    if is_fill_array_type(attribute):
        return AttributeKind.FILL_ARRAY
    if is_attribute_count_size_field(attribute):
        return AttributeKind.SIZE_FIELD

    attribute_type = attribute['type']

    if is_flags_enum(attribute_type):
        return AttributeKind.FLAGS

    if is_struct_type(attribute_type) or is_enum_type(attribute_type) or 'size' not in attribute:
        return AttributeKind.CUSTOM

    attribute_size = attribute['size']

    if isinstance(attribute_size, str):
        if attribute_size.endswith('Size'):
            return AttributeKind.BUFFER
        if attribute_size.endswith('Count'):
            return AttributeKind.ARRAY

    if is_builtin_type(attribute_type, attribute_size):
        return AttributeKind.SIMPLE

    return AttributeKind.BUFFER


class TypeDescriptorDisposition(Enum):
    Inline = 'inline'
    Const = 'const'
    Var = 'var'
    Fill = 'fill'


def indent(code, n_indents=1):
    return ' ' * 4 * n_indents + code


def get_attribute_if_size(attribute_name, attributes, schema):
    value = get_attribute_property_equal(schema, attributes, 'size', attribute_name)
    return value['name'] if value is not None else None


def get_attribute_property_equal(schema, attributes, attribute_name, attribute_value, recurse=True):
    for attribute in attributes:
        if attribute_name in attribute and attribute[attribute_name] == attribute_value:
            return attribute
        if (recurse and 'disposition' in attribute and
                attribute['disposition'] == TypeDescriptorDisposition.Inline.value):
            value = get_attribute_property_equal(schema, schema[attribute['type']]['layout'], attribute_name, attribute_value)
            if value is not None:
                return value
    return None


def get_builtin_type(size):
    builtin_types = {1: 'byte', 2: 'short', 4: 'int', 8: 'long'}
    builtin_type = builtin_types[size]
    return builtin_type


def get_read_method_name(size):
    if isinstance(size, str) or size > 8:
        method_name = 'readFully'
    else:
        type_size_method_name = {1: 'readByte', 2: 'readShort', 4: 'readInt', 8: 'readLong'}
        method_name = type_size_method_name[size]
    return method_name


def get_reverse_method_name(size):
    if isinstance(size, str) or size > 8 or size == 1:
        method_name = '{0}'
    else:
        typesize_methodname = {2: 'Short.reverseBytes({0})',
                               4: 'Integer.reverseBytes({0})',
                               8: 'Long.reverseBytes({0})'}
        method_name = typesize_methodname[size]
    return method_name


def get_write_method_name(size):
    if isinstance(size, str) or size > 8 or size == 0:
        method_name = 'write'
    else:
        typesize_methodname = {1: 'writeByte',
                               2: 'writeShort',
                               4: 'writeInt',
                               8: 'writeLong'}
        method_name = typesize_methodname[size]
    return method_name


def get_generated_type(schema, attribute):
    typename = attribute['type']
    attribute_kind = get_attribute_kind(attribute)
    if attribute_kind in (AttributeKind.SIMPLE, AttributeKind.SIZE_FIELD):
        return get_builtin_type(get_attribute_size(schema, attribute))
    if attribute_kind == AttributeKind.BUFFER:
        return 'ByteBuffer'

    if not is_byte_type(typename):
        typename = get_generated_class_name(typename, attribute, schema)

    if is_any_array_kind(attribute_kind):
        return 'List<{0}>'.format(typename)
    if attribute_kind == AttributeKind.FLAGS:
        return 'EnumSet<{0}>'.format(typename)

    return typename


def get_import_for_type(data_type):
    actual_type = data_type.split('<')[0] if '<' in data_type else data_type

    type_import = {
        'ByteBuffer': 'java.nio.ByteBuffer',
        'ArrayList': 'java.util.ArrayList',
        'EnumSet': 'java.util.EnumSet',
        'List': 'java.util.List',
        'ByteArrayInputStream': 'java.io.ByteArrayInputStream'
    }
    return type_import[actual_type] if actual_type in type_import.keys() else None


def append_period_if_needed(line):
    return line if line.endswith('.') else line + '.'


def get_comment_from_name(name):
    return name[0].upper() + ''.join(' ' + x.lower() if x.isupper() else x for x in name[1:])


def format_description(description):
    formated_description = description[0].upper() + description[1:]
    return append_period_if_needed(formated_description)


def get_comments_if_present(comment):
    if comment:
        return '/** {0} */'.format(format_description(comment))
    return None


def get_comments_from_attribute(attribute, formatted=True):
    comment = attribute['comments'].strip() if 'comments' in attribute else ''
    if not comment and 'name' in attribute:
        comment = get_comment_from_name(attribute['name'])
    return get_comments_if_present(comment) if formatted else comment


def create_enum_name(name):
    enum_name = name[0] + ''.join('_' + x if x.isupper() else x for x in name[1:])
    return enum_name.upper()


def get_default_value(attribute):
    attribute_kind = get_attribute_kind(attribute)
    if attribute_kind == AttributeKind.SIMPLE:
        return '0'
    return 'null'


def get_class_type_from_name(type_name):
    return '{0}.class'.format(type_name)
