#include "modules.h"

#include <demo/sublibA/ConsoleColors.h>

#if PYBIND11_VERSION_AT_LEAST(3,0)
#    include <pybind11/native_enum.h>
#endif

#if PYBIND11_VERSION_AT_LEAST(3,0)
namespace {
enum class NativeColor : int {
    Red = 1,
    Blue = 2,
};
} // namespace
#endif

void bind_enum_module(py::module&&m) {

    py::enum_<demo::sublibA::ConsoleForegroundColor>(m, "ConsoleForegroundColor")
        .value("Green", demo::sublibA::ConsoleForegroundColor::Green)
        .value("Yellow", demo::sublibA::ConsoleForegroundColor::Yellow)
        .value("Blue", demo::sublibA::ConsoleForegroundColor::Blue)
        .value("Magenta", demo::sublibA::ConsoleForegroundColor::Magenta)
        .value("None_", demo::sublibA::ConsoleForegroundColor::None_)
        .export_values();

    m.def(
        "accept_defaulted_enum",
        [](const demo::sublibA::ConsoleForegroundColor &color) {},
        py::arg("color") = demo::sublibA::ConsoleForegroundColor::None_);

#if PYBIND11_VERSION_AT_LEAST(3,0)
    py::native_enum<NativeColor>(m, "NativeColor", "enum.IntEnum")
        .value("Red", NativeColor::Red)
        .value("Blue", NativeColor::Blue)
        .finalize();
#endif
}
