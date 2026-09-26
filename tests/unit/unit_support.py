from pybind11_stubgen import CLIArgs, arg_parser, stub_parser_from_args
from pybind11_stubgen.parser.interface import IParser
from pybind11_stubgen.structs import Annotation, QualifiedName, ResolvedType


def q(name: str) -> QualifiedName:
    return QualifiedName.from_str(name)


def rt(name: str, *parameters: Annotation) -> ResolvedType:
    return ResolvedType(q(name), list(parameters) if parameters else None)


def make_parser(*options: str) -> IParser:
    args = arg_parser().parse_args(
        [*options, "stubgen_test_python"], namespace=CLIArgs()
    )
    return stub_parser_from_args(args)
