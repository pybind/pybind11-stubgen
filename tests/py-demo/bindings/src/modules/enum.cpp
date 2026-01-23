#include "modules.h"

#include <demo/sublibA/ConsoleColors.h>

void bind_enum_module(py::module&&m) {

    py::enum_<demo::sublibA::ConsoleForegroundColor>(m, "ConsoleForegroundColor")
        .value("Green", demo::sublibA::ConsoleForegroundColor::Green, "Green color")
        .value("Yellow", demo::sublibA::ConsoleForegroundColor::Yellow, "Yellow color")
        .value("Blue", demo::sublibA::ConsoleForegroundColor::Blue, "Blue color")
        .value("Magenta", demo::sublibA::ConsoleForegroundColor::Magenta, "Magenta color")
        .value("None_", demo::sublibA::ConsoleForegroundColor::None_, "No color")
        .export_values();

    m.def(
        "accept_defaulted_enum",
        [](const demo::sublibA::ConsoleForegroundColor &color) {},
        py::arg("color") = demo::sublibA::ConsoleForegroundColor::None_);
}
