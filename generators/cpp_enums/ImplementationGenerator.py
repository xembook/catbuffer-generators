from .CppGenerator import CppGenerator

# note: part of formatting happens in CppGenerator, so whenever literal brace needs
# to be produced, it needs to be doubled here

class ImplementationGenerator(CppGenerator):
    def _add_includes(self):
        self.append('#include "{ENUM_NAME}.h"')
        self.append('')

    def _enum_header(self):
        desc = self.schema[self.enum_name]
        self.append('namespace {{')
        self.indent += 1
        self.append('const char* {ENUM_NAME}ToString({ENUM_NAME} value) {{')
        self.indent += 1
        self.append('switch (value) {{')
        self.indent += 1

    def _generate_value(self, formatted_value_name, val, is_last_value):
        self.append('case {{ENUM_NAME}}::{NAME}: return "{NAME}";'.format(NAME=formatted_value_name))

    def _enum_footer(self):
        self.indent -= 1
        self.append('''}}

return nullptr;''')
        self.indent -= 1
        self.append('}}') # end function
        self.indent -= 1
        self.append('}}') # end anon namespace

    def _generate_operator(self):
        self.append('''
std::ostream& operator<<(std::ostream& out, {ENUM_NAME} value) {{
    auto pLabel = {ENUM_NAME}ToString(value);
    if (pLabel)
            out << pLabel;
    else
            out << "{ENUM_NAME}(0x" << utils::HexFormat(utils::to_underlying_type(value)) << ")";

    return out;
}}
''')

