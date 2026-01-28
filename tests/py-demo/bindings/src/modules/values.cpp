#include <pybind11/chrono.h>

#include "modules.h"

#include <chrono>

namespace values_detail {
class Dummy {};
class Foo {};
} // namespace

void bind_values_module(py::module &&m) {
    using namespace values_detail;
    {
        // python module as value
        auto &&pyDummy = py::class_<Dummy>(m, "Dummy");

        pyDummy.def_property_readonly_static(
            "linalg", [](py::object &) { return py::module::import("numpy.linalg"); });

        m.attr("random") = py::module::import("numpy.random");
    }
    {
        py::list li;
        li.append(py::none{});
        li.append(2);
        li.append(py::dict{});
        m.attr("list_with_none") = li;
    }
    {
        auto pyFoo = py::class_<Foo>(m, "Foo");
        m.attr("foovar") = Foo();

        py::list foolist;
        foolist.append(Foo());
        foolist.append(Foo());

        m.attr("foolist") = foolist;
        m.attr("none") = py::none();
    }
    {
        m.attr("t_10ms") = std::chrono::milliseconds(10);
        m.attr("t_20ns") = std::chrono::nanoseconds(20);
        m.attr("t_30s") = std::chrono::seconds(30);

        m.def("add_day",
              [](std::chrono::system_clock::time_point &t) { return t + std::chrono::hours(24); });
    }
}
