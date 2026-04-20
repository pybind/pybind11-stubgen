#pragma once
#include <string>

namespace demo
{
    // note: class stubs must not be sorted
    // https://github.com/sizmailov/pybind11-stubgen/issues/231

    struct MyBase {
      struct Inner{};
      std::string name;
    };

    struct Derived : MyBase {
      int count;
    };

    // Cross-reference test (the "cyclic" case from issue #231 / PR #275):
    // ParIterBase is a base class for ParIter.
    // ParticleContainer references ParIter (via an alias).
    // ParIter.__init__ takes a ParticleContainer& (annotation back-reference).
    // This is NOT cyclic inheritance — just interleaved name usage.

    struct ParIterBase {
      int level;
    };

    struct ParticleContainer;  // forward declaration

    struct ParIter : ParIterBase {
      ParticleContainer* container;
      ParIter(ParticleContainer& pc, int level);
    };

    struct ParticleContainer {
      std::string name;
      void process(ParIter& it);
    };

    inline ParIter::ParIter(ParticleContainer& pc, int level)
        : container(&pc), ParIterBase{level} {}

    inline void ParticleContainer::process(ParIter& it) {
        it.level += 1;
    }
}
