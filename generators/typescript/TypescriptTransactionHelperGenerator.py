from .Helpers import indent


# pylint: disable=too-few-public-methods
class TypescriptTransactionHelperGenerator():
    """Typescript trenasction helper class generator"""

    def __init__(self, class_name, entity_type_enum_value, embedded):
        self.class_output = []
        self.class_name = class_name
        self.imports = []
        self.embedded = embedded
        self.enum_list = entity_type_enum_value
        self._add_import('EntityTypeDto')
        if self.embedded:
            self._add_import('EmbeddedTransactionBuilder')
        else:
            self._add_import('TransactionBuilder')
        self._add_import('GeneratorUtils')

    def _read_file(self):
        load_from_binary_method = self._write_load_from_binary_method()
        self.class_output += sorted(self.imports)
        self.class_output += ['']
        line = ['/** Helper class for embedded transaction serialization */']
        line += ['export class {0} {{'.format(self.class_name)]
        line += ['']
        if self.embedded:
            line += self._write_serialize_embedded_transaction_method()
            line += ['']
        line += load_from_binary_method
        line += ['']
        if self.embedded:
            line += self._write_size_getter()
        line += ['}']
        self.class_output += line

    @classmethod
    def _write_serialize_embedded_transaction_method(cls):
        line = [indent('/** Serialize an transaction */')]
        line += [indent('public static serialize(transaction: EmbeddedTransactionBuilder): Uint8Array {')]
        line += [indent('const byte = transaction.serialize();', 2)]
        line += [indent('const padding = new Uint8Array(GeneratorUtils.getTransactionPaddingSize(byte.length, 8));', 2)]
        line += [indent('return GeneratorUtils.concatTypedArrays(byte, padding);', 2)]
        line += [indent('}')]
        return line

    def _write_load_from_binary_method(self):

        if self.embedded:
            line = [indent('/** Deserialize an embedded transaction from binary */')]
            line += [indent('public static loadFromBinary(bytes: Uint8Array): EmbeddedTransactionBuilder {')]
            line += [indent('const header = EmbeddedTransactionBuilder.loadFromBinary(bytes);', 2)]
        else:
            line = [indent('/** Deserialize an transaction from binary */')]
            line += [indent('public static loadFromBinary(bytes: Uint8Array): TransactionBuilder {')]
            line += [indent('const header = TransactionBuilder.loadFromBinary(bytes);', 2)]
        line += [indent('switch (header.getType()) {', 2)]
        for name, value_comments in self.enum_list.items():
            # pylint: disable=unused-variable
            value, comments = value_comments
            if (value != 0 and not name.upper().startswith('AGGREGATE') and self.embedded and not name.upper().startswith('BLOCK')):
                builder_class = 'Embedded{0}'.format(''.join([a.capitalize() for a in name.split('_')]))
                self._add_import(builder_class)
                line += [indent('case EntityTypeDto.{0}:'.format(name), 3)]
                line += [indent('return {0}.loadFromBinary(bytes);'.format(builder_class), 4)]
            elif (value != 0 and not self.embedded) and not name.upper().startswith('BLOCK'):
                builder_class = '{0}'.format(''.join([a.capitalize() for a in name.split('_')]))
                self._add_import(builder_class)
                line += [indent('case EntityTypeDto.{0}:'.format(name), 3)]
                line += [indent('return {0}.loadFromBinary(bytes);'.format(builder_class), 4)]

        line += [indent('default:', 3)]
        line += [indent('throw new Error(`Transaction type: ${header.getType()} not recognized.`);', 4)]
        line += [indent('}', 2)]
        line += [indent('}')]
        return line

    @classmethod
    def _write_size_getter(cls):
        line = [indent('/** Get actual embedded transaction size */')]
        line += [indent('public static getEmbeddedTransactionSize(transactions: EmbeddedTransactionBuilder[]): number {')]
        line += [indent('return transactions.map((o) => EmbeddedTransactionHelper.serialize(o).length).reduce((a, b) => a + b, 0);', 2)]
        line += [indent('}')]
        return line

    def _add_import(self, name):
        self.imports += ['import {{ {0} }} from \'./{0}\';'.format(name)]

    def generate(self):
        self._read_file()

        return self.class_output
