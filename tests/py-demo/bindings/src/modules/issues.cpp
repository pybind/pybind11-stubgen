#include "modules.h"

void bind_issues_module(py::module &&m) {
    {
        // https://github.com/sizmailov/pybind11-stubgen/issues/51
        m.def(
            "issue_51_catastrophic_regex", [](int *, int *) {}, R"docstring(

    Use-case:
        issue_51(os.get_handle_inheritable, os.set_handle_inheritable))docstring");
    }
    {
        // https://github.com/sizmailov/pybind11-stubgen/issues/73
        m.def(
            "issue_73_utf8_doc_chars",
            [] {},
            py::doc("Construct a Ramsete unicycle controller.\n"
                    "\n"
                    "Tuning parameter (b > 0 rad²/m²) for which larger values make\n"
                    "\n"
                    "convergence more aggressive like a proportional term.\n"
                    "Tuning parameter (0 rad⁻¹ < zeta < 1 rad⁻¹) for which larger\n"
                    "values provide more damping in response."));
    }
    {
        m.def("backslashes_should_be_escaped", [] {}, R"docstring(
            \brief A brief description of this function.

            A detailed description of this function.

            Here's some reStructuredText: :math:`x = [x, y, \theta]^T`
        )docstring");
    }
    {
        // https://github.com/sizmailov/pybind11-stubgen/issues/86
        auto cleanup_callback = []() { /* ... */ };
        m.attr("_cleanup") = py::capsule(cleanup_callback);
    }
    {
        m.def("issue_274_docstring_leading_newline", [](){}, py::doc("\nThis is a docstring"));
    }
}
