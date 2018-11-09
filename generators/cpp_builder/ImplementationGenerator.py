from .CppGenerator import CppGenerator, FieldKind, capitalize

SUFFIX = 'Transaction'


class ImplementationGenerator(CppGenerator):
    def _add_includes(self):
        self.append('#include "{BUILDER_NAME}.h"')
        self.append('')

    def _class_header(self):
        self.append('{BUILDER_NAME}::{BUILDER_NAME}(model::NetworkIdentifier networkIdentifier, const Key& signer)')
        self.indent += 2
        self.append(': TransactionBuilder(networkIdentifier, signer)')
        self.indent -= 2
        self.append('{{}}')
        self.append('')

    def _generate_setter(self, field_kind, field, full_setter_name, param_name):
        self.append('void {BUILDER_NAME}::' + full_setter_name + ' {{')
        self.indent += 1
        if field_kind == FieldKind.SIMPLE:
            self.append('m_{NAME} = {NAME};'.format(NAME=param_name))
        elif field_kind == FieldKind.BUFFER:
            self.append("""if (0 == {NAME}.Size)
\tCATAPULT_THROW_INVALID_ARGUMENT("argument cannot be empty");

if (!m_{NAME}.empty())
\tCATAPULT_THROW_RUNTIME_ERROR("field already set");

m_{NAME}.resize({NAME}.Size);
m_{NAME}.assign({NAME}.pData, {NAME}.pData + {NAME}.Size);""".format(NAME=param_name))
        else:
            self.append('m_{FIELD}.push_back({PARAM});'.format(FIELD=field['name'], PARAM=param_name))
        self.indent -= 1
        self.append('}}\n')

    def _generate_field(self, field_kind, field, builder_field_typename):
        pass

    def _generate_build_variable_fields_size(self, variable_sizes, field):
        field_kind = CppGenerator._get_field_kind(field)
        formatted_vector_size = 'm_{NAME}.size()'.format(NAME=field['name'])
        if field_kind == FieldKind.BUFFER:
            self.append('size += {};'.format(formatted_vector_size))
        elif field_kind == FieldKind.VECTOR:
            qualified_typename = self.qualified_type(field['type'])
            formatted_size = '{ARRAY_SIZE} * sizeof({TYPE})'.format(ARRAY_SIZE=formatted_vector_size, TYPE=qualified_typename)
            self.append('size += {};'.format(formatted_size))

        if field_kind != FieldKind.SIMPLE:
            variable_sizes[field['size']] = formatted_vector_size

    def _generate_build_variable_fields(self, field):
        field_kind = CppGenerator._get_field_kind(field)
        if field_kind == FieldKind.SIMPLE:
            return

        template = {'NAME': field['name'], 'TX_FIELD_NAME': capitalize(field['name'])}
        if field_kind == FieldKind.BUFFER:
            self.append('if (!m_{NAME}.empty())'.format(**template))
            self.indent += 1
            self.append('std::copy(m_{NAME}.cbegin(), m_{NAME}.cend(), pTransaction->{TX_FIELD_NAME}Ptr());'.format(**template))
            self.indent -= 1
            self.append('')
        elif field_kind == FieldKind.VECTOR:
            self.append('if (!m_{NAME}.empty()) {{{{'.format(NAME=field['name']))
            self.indent += 1

            self.append('auto* pElement = pTransaction->{TX_FIELD_NAME}Ptr();'.format(**template))
            self.append('for (const auto& element : m_{NAME}) {{{{'.format(**template))
            self.indent += 1

            self.append('*pElement = element;')
            self.append('++pElement;')

            self.indent -= 1
            self.append('}}')
            self.indent -= 1
            self.append('}}')

    @staticmethod
    def byte_size_to_type_name(size):
        return {1: 'uint8_t', 2: 'uint16_t', 4: 'uint32_t', '8': 'uint64_t'}[size]

    def _generate_build(self):
        self.append('template<typename TransactionType>')
        self.append('std::unique_ptr<TransactionType> {BUILDER_NAME}::buildImpl() const {{')
        self.indent += 1

        self.append('// 1. allocate, zero (header), set model::Transaction fields')
        self.append('auto size = sizeof(TransactionType);')
        # go through variable data and add it to size, collect sizes
        variable_sizes = {}
        self._foreach_builder_field(lambda field: self._generate_build_variable_fields_size(variable_sizes, field))
        self.append('auto pTransaction = createTransaction<TransactionType>(size);')
        self.append('')

        self.append('// 2. set transaction fields and sizes')

        # set non-variadic fields
        for field in self.schema[self.transaction_body_name()]['layout']:
            template = {'NAME': field['name'], 'TX_FIELD_NAME': capitalize(field['name'])}
            if field['name'].endswith('Size') or field['name'].endswith('Count'):
                size = variable_sizes[field['name']]
                size_type = ImplementationGenerator.byte_size_to_type_name(field['size'])
                format_string = 'pTransaction->{TX_FIELD_NAME} = utils::checked_cast<size_t, {SIZE_TYPE}>({SIZE});'
                self.append(format_string.format(**template, SIZE_TYPE=size_type, SIZE=size))
            else:
                field_kind = CppGenerator._get_field_kind(field)
                if field_kind == FieldKind.SIMPLE:
                    self.append('pTransaction->{TX_FIELD_NAME} = m_{NAME};'.format(**template))
                # variadic fields are defined at the end of schema,
                # so break if loop reached any of them
                else:
                    break
        self.append('')

        self.append('// 3. set variable transaction fields')
        self._foreach_builder_field(self._generate_build_variable_fields)

        self.append('')
        self.append('return pTransaction;')
        self.indent -= 1
        self.append('}}')

    def _builds(self):
        self.append("""std::unique_ptr<{BUILDER_NAME}::Transaction> {BUILDER_NAME}::build() const {{
\treturn buildImpl<Transaction>();
}}

std::unique_ptr<{BUILDER_NAME}::EmbeddedTransaction> {BUILDER_NAME}::buildEmbedded() const {{
\treturn buildImpl<EmbeddedTransaction>();
}}
""")
        self._generate_build()

    def _class_footer(self):
        pass
