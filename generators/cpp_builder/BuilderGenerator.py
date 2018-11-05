from .HeaderGenerator import HeaderGenerator
from .ImplementationGenerator import ImplementationGenerator
from generators.Descriptor import Descriptor
from collections import namedtuple


class BuilderGenerator:
    """Cpp transaction builder generator, creates both header and implementation file"""
    def __init__(self, schema):
        self.schema = schema

    def __iter__(self):
        """Creates an iterator around this generator"""
        self.current = iter(self.schema)
        self.generated_header = False
        return self

    def _iterate_until_next_transaction(self):
        if self.generated_header:
            return

        name = next(self.current)
        while name == 'Transaction' or name.startswith('Embedded') or not name.endswith('Transaction'):
            name = next(self.current)
        return name

    def __next__(self):
        """Returns Descriptor with desired filename and generated file content"""
        if self.generated_header:
            generator = ImplementationGenerator(self.schema, self.current_name)
            self.code = generator.generate()
            self.generated_header = False
            return Descriptor('{}.cpp'.format(generator.builder_name), self.code)
        else:
            self.current_name = self._iterate_until_next_transaction()
            generator = HeaderGenerator(self.schema, self.current_name)
            self.code = generator.generate()
            self.generated_header = True
            return Descriptor('{}.h'.format(generator.builder_name), self.code)
