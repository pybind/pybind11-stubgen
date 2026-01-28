#include "modules.h"

#include <demo/Foo.h>
#include <demo/sublibA/ConsoleColors.h>

namespace aliases_detail {
    class Dummy {
    };

    struct Color {
    };

    struct Bar1 {
    };
    struct Bar2 {
    };
    struct Bar3 {
    };
    struct Bar4 {
    };
} // namespace

void bind_aliases_module(py::module &&m) {
    using namespace aliases_detail;
    {
        // python module as value
        auto &&pyDummy = py::class_<Dummy>(m, "Dummy");

        pyDummy.def_property_readonly_static(
                "linalg", [](py::object &) { return py::module::import("numpy.linalg"); });

        m.add_object("random", py::module::import("numpy.random"));
    }

    {
        auto &&pyColor = py::class_<Color>(m, "Color");

        m.def("func", [](int x) { return x + 1; });

        m.attr("local_type_alias") = pyColor;
        m.attr("local_func_alias") = m.attr("func");
    }
    {
        auto &&sub = m.def_submodule("foreign_attr");
        sub.attr("value") = demo::Foo();
    }
    {
        auto &&sub = m.def_submodule("foreign_arg");
        sub.def("set_foo", [](demo::Foo &) { return 13; });
    }
    {
        auto &&sub = m.def_submodule("foreign_return");
        sub.def("get_foo", []() { return demo::Foo(); });
    }
    {
        auto &&sub = m.def_submodule("foreign_class_member");
        auto &&pyBar = py::class_<Bar1>(sub, "Bar1");
        pyBar.attr("foo") = demo::Foo();
    }
    {
        auto &&sub = m.def_submodule("foreign_method_arg");
        auto &&pyBar = py::class_<Bar2>(sub, "Bar2");
        pyBar.def("set_foo", [](const Bar2 &, const demo::Foo &) { return 13; });
    }
    {
        auto &&sub = m.def_submodule("foreign_method_return");
        auto &&pyBar = py::class_<Bar3>(sub, "Bar3");
        pyBar.def("get_foo", []() { return demo::Foo(); });
    }
    {
        auto &&sub = m.def_submodule("missing_self_arg");
        auto &&pyBar = py::class_<Bar4>(sub, "Bar4");
        pyBar.def("set_foo", [](const demo::Foo &) { return 13; });
    }

    {
        m.attr("foreign_type_alias") = m.attr("foreign_method_arg").attr("Bar2");
        m.attr("foreign_class_alias") = m.attr("foreign_return").attr("get_foo");
    }

    m.def(
            "foreign_enum_default",
            [](const py::object & /* color */) {},
            py::arg("color") = demo::sublibA::ConsoleForegroundColor::Blue
    );
}
