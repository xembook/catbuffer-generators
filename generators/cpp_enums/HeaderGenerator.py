from .CppGenerator import CppGenerator, capitalize

# note: part of formatting happens in CppGenerator, so whenever literal brace needs
# to be produced, it needs to be doubled here

class HeaderGenerator(CppGenerator):
    def _add_includes(self):
        self.append('#pragma once')
        self.append('#include <iosfwd>')
        self.append('')

    def enumType(self, desc):
        return self._builtin_type(desc['size'], desc['signedness'])


    def _enum_header(self):
        desc = self.schema[self.enum_name]
        self._add_comment(desc['comments'])
        enumLine = 'enum class {ENUM_NAME} : ' + self.enumType(desc) + ' {{'
        self.append(enumLine)
        self.indent += 1

    def _add_comment(self, comment):
        self.append('/// {}.'.format(capitalize(comment)))

    def _generate_value(self, formatted_value_name, val, is_last_value):
        formatted_value_format = '{}' if 'formatting' not in self.hints else self.hints['formatting']
        formatted_value = formatted_value_format.format(val['value'])
        self._add_comment(val['comments'])
        suffix = '' if is_last_value else ','
        self.append('{NAME} = {VALUE}{SUFFIX}'.format(NAME=formatted_value_name, VALUE=formatted_value, SUFFIX=suffix))

        if not is_last_value:
            self.append('')

    def _enum_footer(self):
        self.indent -= 1
        self.append('}};')

    def _generate_operator(self):
        self.append('''
// Insertion operator for outputting \\a value to \\a out.
std::ostream& operator<<(std::ostream& out, {ENUM_NAME} value);''')

