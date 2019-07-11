# pylint: disable=too-few-public-methods
from generators.Descriptor import Descriptor
from .HeaderGenerator import HeaderGenerator
from .ImplementationGenerator import ImplementationGenerator


class EnumGenerator:
    """Cpp enum generator, creates both header and implementation file"""
    def __init__(self, schema, options):
        self.schema = schema
        self.options = options
        self.current = None
        self.generated_header = False
        self.current_name = None

    def __iter__(self):
        """Creates an iterator around this generator"""
        self.current = iter(self.schema)
        self.generated_header = False
        return self

    def _get_next(self):
        if self.generated_header:
            return None

        name = next(self.current)
        return name

    def __next__(self):
        """Returns Descriptor with desired filename and generated file content"""
        if not self.generated_header:
            self.current_name = self._get_next()
            generator = HeaderGenerator(self.schema, self.options, self.current_name)
            code = generator.generate()
            self.generated_header = True
            return Descriptor('{}.h'.format(generator.enum_name), code)

        generator = ImplementationGenerator(self.schema, self.options, self.current_name)
        code = generator.generate()
        self.generated_header = False
        return Descriptor('{}.cpp'.format(generator.enum_name), code)
