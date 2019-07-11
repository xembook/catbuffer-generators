from generators.cpp_builder.BuilderGenerator import BuilderGenerator
from generators.cpp_enums.EnumGenerator import EnumGenerator
from generators.java.JavaFileGenerator import JavaFileGenerator

AVAILABLE_GENERATORS = {
    'cpp_builder': BuilderGenerator,
    'cpp_enums': EnumGenerator,
    'java': JavaFileGenerator
}
