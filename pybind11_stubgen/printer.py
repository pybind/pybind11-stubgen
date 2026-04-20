from __future__ import annotations

import dataclasses
import logging
import sys

from pybind11_stubgen.structs import (
    Alias,
    Annotation,
    Argument,
    Attribute,
    Class,
    Docstring,
    Field,
    Function,
    Identifier,
    Import,
    InvalidExpression,
    Method,
    Modifier,
    Module,
    Property,
    ResolvedType,
    TypeVar_,
    Value,
)

log = logging.getLogger("pybind11_stubgen")


def indent_lines(lines: list[str], by=4) -> list[str]:
    return [" " * by + line for line in lines]


def _referenced_local_dependency_name(expr: str) -> str | None:
    """Extract the local dependency name from a dotted identifier expression.

    Returns the first component if *expr* is a valid dotted identifier
    (e.g. ``"ParIter"`` -> ``"ParIter"``, ``"Outer.Inner"`` -> ``"Outer"``),
    or ``None`` for anything else (literals, calls, etc.).
    """
    parts = expr.split(".")
    if not parts or any(not part.isidentifier() for part in parts):
        return None
    return parts[0]


def _topological_sort_classes(classes: list[Class]) -> list[Class]:
    """Sort classes so that dependencies appear before dependents.

    Considers two kinds of edges:
    - Inheritance: base classes must appear before derived classes.
    - Runtime references: class-body aliases (``Foo = Bar``) and field
      values that name a sibling class are executable at import time,
      so the referenced class must already be defined.
      (``from __future__ import annotations`` only defers *type annotations*,
      not attribute/alias assignments.)

    Uses Kahn's algorithm. Ties are broken by input position for stability.
    Only references whose first identifier component names a sibling class in
    the current scope contribute edges. External references are ignored.
    """
    if not classes:
        return classes

    name_to_index = {c.name: i for i, c in enumerate(classes)}
    name_to_class = {c.name: c for c in classes}

    # Build adjacency list: dependency -> [dependent, ...]
    # and in-degree count for each class
    children: dict[str, list[str]] = {c.name: [] for c in classes}
    in_degree: dict[str, int] = {c.name: 0 for c in classes}
    seen_edges: set[tuple[str, str]] = set()

    def _add_edge(dependency: str, dependent: str) -> None:
        edge = (dependency, dependent)
        if edge in seen_edges:
            return
        seen_edges.add(edge)
        children[dependency].append(dependent)
        in_degree[dependent] += 1

    for c in classes:
        # Inheritance edges: base -> derived
        for base in c.bases:
            base_name = str(base[0])
            if base_name in name_to_class:
                _add_edge(base_name, c.name)

        # Alias edges: ``Iterator = ParIter`` is a runtime assignment
        for alias in c.aliases:
            origin_name = str(alias.origin[0])
            if origin_name in name_to_class and origin_name != c.name:
                _add_edge(origin_name, c.name)

        # Field-value edges: a print-safe field like ``Iterator = ParIter``
        # (parsed as a Field rather than an Alias in some configurations)
        for field in c.fields:
            val = field.attribute.value
            if val is not None and val.is_print_safe:
                val_name = _referenced_local_dependency_name(val.repr)
                if (
                    val_name is not None
                    and val_name in name_to_class
                    and val_name != c.name
                ):
                    _add_edge(val_name, c.name)

    # Initialize queue with zero in-degree classes, sorted by input position
    queue = sorted(
        [name for name, deg in in_degree.items() if deg == 0],
        key=lambda n: name_to_index[n],
    )

    result = []
    while queue:
        name = queue.pop(0)
        result.append(name_to_class[name])
        # Sort children by input position for stable ordering
        for child in sorted(children[name], key=lambda n: name_to_index[n]):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)
        # Re-sort queue to maintain input-position priority
        queue.sort(key=lambda n: name_to_index[n])

    if len(result) < len(classes):
        remaining = [c for c in classes if c.name not in {r.name for r in result}]
        log.warning(
            "Cycle detected in class dependencies involving: %s. "
            "Appending in original order.",
            [c.name for c in remaining],
        )
        result.extend(remaining)

    return result


class Printer:
    def __init__(
        self,
        invalid_expr_as_ellipses: bool,
        print_value_comments: bool = False,
    ):
        self.invalid_expr_as_ellipses = invalid_expr_as_ellipses
        self.print_value_comments = print_value_comments

    def _order_classes(self, classes: list[Class]) -> list[Class]:
        return _topological_sort_classes(classes)

    def print_alias(self, alias: Alias) -> list[str]:
        return [f"{alias.name} = {alias.origin}"]

    def print_attribute(self, attr: Attribute) -> list[str]:
        parts = [
            f"{attr.name}",
        ]
        if attr.annotation is not None:
            parts.append(f": {self.print_annotation(attr.annotation)}")

        if attr.value is not None and attr.value.is_print_safe:
            parts.append(f" = {self.print_value(attr.value)}")
        else:
            if attr.annotation is None:
                parts.append(" = ...")
            if attr.value is not None and self.print_value_comments:
                parts.append(f"  # value = {self.print_value(attr.value)}")

        return ["".join(parts)]

    def print_argument(self, arg: Argument) -> str:
        parts = []
        if arg.variadic:
            parts += ["*"]
        if arg.kw_variadic:
            parts += ["**"]
        parts.append(f"{arg.name}")
        if arg.annotation is not None:
            parts.append(f": {self.print_annotation(arg.annotation)}")
        if isinstance(arg.default, Value):
            if arg.default.is_print_safe:
                parts.append(f" = {self.print_value(arg.default)}")
            else:
                parts.append(" = ...")
        elif isinstance(arg.default, InvalidExpression):
            parts.append(f" = {self.print_invalid_exp(arg.default)}")

        return "".join(parts)

    def print_class(self, class_: Class) -> list[str]:
        if class_.bases:
            base_list = "(" + ", ".join(str(base) for base in class_.bases) + ")"
        else:
            base_list = ""
        return [
            f"class {class_.name}{base_list}:",
            *indent_lines(self.print_class_body(class_)),
        ]

    def print_type_var(self, type_var: TypeVar_) -> list[str]:
        return [str(type_var)]

    def print_class_body(self, class_: Class) -> list[str]:
        result = []
        if class_.doc is not None:
            result.extend(self.print_docstring(class_.doc))

        for sub_class in self._order_classes(class_.classes):
            result.extend(self.print_class(sub_class))

        modifier_order: dict[Modifier, int] = {
            "static": 0,
            "class": 1,
            None: 2,
        }
        for field in sorted(
            class_.fields, key=lambda f: (modifier_order[f.modifier], f.attribute.name)
        ):
            result.extend(self.print_field(field))

        for alias in sorted(class_.aliases, key=lambda a: a.name):
            result.extend(self.print_alias(alias))

        for method in sorted(
            class_.methods, key=lambda m: (modifier_order[m.modifier], m.function.name)
        ):
            result.extend(self.print_method(method))

        for prop in sorted(class_.properties, key=lambda p: p.name):
            result.extend(self.print_property(prop))

        if not result:
            result = ["pass"]

        return result

    def print_docstring(self, doc: Docstring) -> list[str]:
        return [
            '"""',
            *(
                line.replace("\\", r"\\").replace('"""', r"\"\"\"")
                for line in doc.lstrip("\n").splitlines()
            ),
            '"""',
        ]

    def print_field(self, field: Field) -> list[str]:
        return self.print_attribute(field.attribute)  # FIXME: modifier

    def print_function(self, func: Function) -> list[str]:
        pos_only = False
        kw_only = False

        args = []
        for arg in func.args:
            if arg.variadic:
                pos_only = True
                kw_only = True
            if not pos_only and not arg.pos_only:
                pos_only = True
                if sys.version_info >= (3, 8):
                    args.append("/")
            if not kw_only and arg.kw_only:
                kw_only = True
                args.append("*")
            args.append(self.print_argument(arg))
        if len(args) > 0 and args[0] == "/":
            args = args[1:]
        signature = [f"def {func.name}"]

        if func.type_vars:
            signature.extend(["[", ", ".join(func.type_vars), "]"])

        signature.extend(
            [
                "(",
                ", ".join(args),
                ")",
            ]
        )

        if func.returns is not None:
            signature.append(f" -> {self.print_annotation(func.returns)}")
        signature.append(":")

        result: list[str] = [
            *(f"@{decorator}" for decorator in func.decorators),
            "".join(signature),
        ]

        if func.doc is not None:
            body = self.print_docstring(func.doc)
        else:
            body = ["..."]

        result.extend(indent_lines(body))

        return result

    def print_submodule_import(self, name: Identifier) -> list[str]:
        return [f"from . import {name}"]

    def print_import(self, import_: Import) -> list[str]:
        parent = str(import_.origin.parent)
        if import_.name is None:
            return [f"import {import_.origin}"]

        if len(parent) == 0:
            return [f"import {import_.origin} as {import_.name}"]

        result = f"from {parent} import {import_.origin[-1]}"
        if import_.name != import_.origin[-1]:
            result += f" as {import_.name}"
        return [result]

    def print_method(self, method: Method) -> list[str]:
        result = []
        if method.modifier == "static":
            result += ["@staticmethod"]
        elif method.modifier == "class":
            result += ["@classmethod"]
        elif method.modifier is None:
            pass
        else:
            raise RuntimeError()
        result.extend(self.print_function(method.function))
        return result

    def print_module(self, module: Module) -> list[str]:
        result = []

        if module.doc is not None:
            result.extend(self.print_docstring(module.doc))

        for import_ in sorted(module.imports, key=lambda x: (x.origin, x.name or "")):
            result.extend(self.print_import(import_))

        for sub_module in module.sub_modules:
            result.extend(self.print_submodule_import(sub_module.name))

        # Place __all__ above everything
        for attr in sorted(module.attributes, key=lambda a: a.name):
            if attr.name == "__all__":
                result.extend(self.print_attribute(attr))
                break

        for type_var in sorted(module.type_vars, key=lambda t: t.name):
            result.extend(self.print_type_var(type_var))

        for class_ in self._order_classes(module.classes):
            result.extend(self.print_class(class_))

        for func in sorted(module.functions, key=lambda f: f.name):
            result.extend(self.print_function(func))

        for attr in sorted(module.attributes, key=lambda a: a.name):
            if attr.name != "__all__":
                result.extend(self.print_attribute(attr))

        for alias in module.aliases:
            result.extend(self.print_alias(alias))

        return result

    def print_property(self, prop: Property) -> list[str]:
        if not prop.getter:
            # FIXME: support setter-only props
            return []

        # FIXME: add modifier
        result = []

        result.extend(
            [
                "@property",
                *self.print_function(
                    dataclasses.replace(
                        prop.getter,
                        name=prop.name,
                        # replace getter docstring if prop.doc exists
                        doc=prop.doc if prop.doc is not None else prop.getter.doc,
                    )
                ),
            ]
        )
        if prop.setter:
            result.extend(
                [
                    f"@{prop.name}.setter",
                    *self.print_function(
                        dataclasses.replace(
                            prop.setter,
                            name=prop.name,
                            # remove setter docstring if prop.doc exists
                            doc=None if prop.doc is not None else prop.setter.doc,
                        )
                    ),
                ]
            )

        return result

    def print_value(self, value: Value) -> str:
        split = value.repr.split("\n", 1)
        if len(split) == 1:
            return split[0]
        else:
            return split[0] + "..."

    def print_type(self, type_: ResolvedType) -> str:
        if (
            str(type_.name) == "typing.Optional"
            and type_.parameters is not None
            and len(type_.parameters) == 1
        ):
            return f"{self.print_annotation(type_.parameters[0])} | None"
        if str(type_.name) == "typing.Union" and type_.parameters is not None:
            return " | ".join(self.print_annotation(p) for p in type_.parameters)
        if type_.parameters:
            param_str = (
                "["
                + ", ".join(self.print_annotation(p) for p in type_.parameters)
                + "]"
            )
        else:
            param_str = ""
        return f"{type_.name}{param_str}"

    def print_annotation(self, annotation: Annotation) -> str:
        if isinstance(annotation, ResolvedType):
            return self.print_type(annotation)
        elif isinstance(annotation, Value):
            return self.print_value(annotation)
        elif isinstance(annotation, InvalidExpression):
            return self.print_invalid_exp(annotation)
        else:
            raise AssertionError()

    def print_invalid_exp(self, invalid_expr: InvalidExpression) -> str:
        if self.invalid_expr_as_ellipses:
            return "..."
        return invalid_expr.text
