from generators.cpp_builder.BuilderGenerator import BuilderGenerator
from generators.java.JavaFileGenerator import JavaFileGenerator

AVAILABLE_GENERATORS = {
    'cpp_builder': BuilderGenerator,
    'java': JavaFileGenerator
}
