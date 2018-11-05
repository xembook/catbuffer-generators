from .CppGenerator import CppGenerator, FieldKind, uncapitalize
import re

# note: part of formatting happens in CppGenerator, so whenever literal brace needs
# to be produced, it needs to be doubled here


class HeaderGenerator(CppGenerator):
    def __init__(self, schema, name):
        super(HeaderGenerator, self).__init__(schema, name)

    def _add_includes(self):
        self.append("""#pragma once
#include "TransactionBuilder.h"
#include "plugins/txes/{PLUGIN}/src/model/{{TRANSACTION_NAME}}.h"
#include <vector>
""".format(PLUGIN=self.hints['plugin']))

    def _class_header(self):
        self.append('/// Builder for a {COMMENT_NAME} transaction.')
        self.append('class {BUILDER_NAME} : public TransactionBuilder {{')
        self.append('public:')

        self.indent += 1
        self.append('using Transaction = model::{TRANSACTION_NAME};')
        self.append('using EmbeddedTransaction = model::Embedded{TRANSACTION_NAME};')
        self.append('')
        self.append('/// Creates a {COMMENT_NAME} builder for building a {COMMENT_NAME} transaction from \\a signer')
        self.append('/// for network specified by \\a networkIdentifier.')
        self.append('{BUILDER_NAME}(model::NetworkIdentifier networkIdentifier, const Key& signer);')
        self.append('')
        self.indent -= 1

    def _add_comment(self, field_kind, field):
        comments = {
            FieldKind.SIMPLE: 'Sets the {COMMENT} field to \\a {NAME}.',
            FieldKind.BUFFER: 'Sets the {COMMENT} field to \\a {NAME}.',
            FieldKind.VECTOR: 'Adds \\a {NAME} to {COMMENT}.'
        }
        name = field['name'] if field_kind != FieldKind.VECTOR else uncapitalize(field['type'])
        self.append('/// ' + comments[field_kind].format(COMMENT=field['comments'], NAME=name))

    def _generate_setter(self, field_kind, field, full_setter_name, param_name):
        self._add_comment(field_kind, field)
        self.append('void {};\n'.format(full_setter_name))

    def _setters(self):
        self.append('public:')
        self.indent += 1
        super(HeaderGenerator, self)._setters()
        self.indent -= 1

    def _builds(self):
        self.append('public:')
        self.indent += 1
        self.append("""/// Builds a new {COMMENT_NAME} transaction.
std::unique_ptr<Transaction> build() const;

/// Builds a new embedded {COMMENT_NAME} transaction.
std::unique_ptr<EmbeddedTransaction> buildEmbedded() const;
""")
        self.indent -= 1

        self.append('private:')
        self.indent += 1
        self.append("""template<typename TTransaction>
std::unique_ptr<TTransaction> buildImpl() const;
""")
        self.indent -= 1

    def _generate_field(self, field_kind, field, builder_field_typename):
        self.append('{TYPE} m_{NAME};'.format(TYPE=builder_field_typename, NAME=field['name']))

    def _privates(self):
        self.append('private:')
        self.indent += 1
        super(HeaderGenerator, self)._privates()
        self.indent -= 1

    def _class_footer(self):
        self.append('}};')
