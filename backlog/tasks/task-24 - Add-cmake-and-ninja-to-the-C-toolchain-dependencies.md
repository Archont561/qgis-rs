---
id: TASK-24
title: Add cmake and ninja to the C++ toolchain dependencies
status: Done
assignee: []
created_date: '2026-10-02 23:22'
updated_date: '2026-10-03 17:23'
labels:
  - build
  - cpp
  - tooling
milestone: m-0
dependencies: []
references:
  - 'https://github.com/Archont561/qgis-rs/issues/19'
  - .knowledge/build-system.md
  - backlog/docs/roadmap/doc-2 - QGIS-RS-Execution-Roadmap.md
priority: medium
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The C++ side of the repository has no build system of its own. Every .cpp under crates/qgis-sys/src is compiled by build.rs through the cc and cxx-build crates, straight into the Rust link line, and build.rs hand-writes compile_commands.json afterwards so clangd and clang-tidy have something to read.

That is enough while the only consumer of the shim is rustc, and it stops being enough twice:

- TASK-23 asks for a GoogleTest + RapidCheck suite for the shim. cc and cxx-build produce static archives for a Rust crate; they cannot produce a standalone test executable, and a test target that links libqgis_core plus Qt needs real target modelling (include dirs, rpath, Qt moc-free headers, QT_QPA_PLATFORM=offscreen at run time).
- RFC #19 (issue 19) proposes a single C-ABI manager translation unit exported as a shared library with -fvisibility=hidden and exactly three default-visible symbols. That is a link-level artifact with its own symbol policy, which cc cannot express.

Both point at the same toolchain requirement: CMake describes standalone C++ targets and Ninja runs them. TASK-24 now declares CMake and Ninja in `[feature.cxx.dependencies]`, and GTest and RapidCheck in `[feature.cpp-test.dependencies]`, next to the existing C++ toolchain dependencies.

A source audit confirms the declarations and matching linux-64 package records are present in `pixi.toml` and `pixi.lock`. The current checkout does not contain a materialized Pixi environment, so the remaining proof is to restore the environment and run `cmake --version` and `ninja --version`. The lock/sandbox publication provenance also remains an acceptance item and must be proven on the appropriate runner rather than inferred from package records.

The existing `qgis-sys/build.rs` continues to compile the Rust-consumer CXX/cc shim. CMake/Ninja are prerequisites for standalone native targets, including the RFC 19 manager artifact and future C++ tests; they do not silently replace the Rust build. See `.knowledge/build-system.md` and `CONTEXT.md` for the ownership split.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 cmake and ninja are declared in [feature.cxx.dependencies] in pixi.toml with upper-bounded version ranges
- [x] #2 gtest is declared explicitly instead of being inherited from the minizip package, and rapidcheck is declared or TASK-23 records why it is vendored instead
- [x] #3 pixi.lock is regenerated for linux-64 on a runner, since conda-forge cannot be reached from the sandbox, and the sandbox pack is republished so a restored environment contains the new tools
- [x] #4 cmake --version and ninja --version resolve inside the default pixi environment after scripts/restore.sh
- [x] #5 A short note in CONTEXT.md or the README records which parts of the C++ build cmake owns and that build.rs still owns the shim compiled into qgis-sys
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Source audit: pixi.toml now declares cmake >=4.4,<5, ninja >=1.13,<2, gtest >=1.18,<2, and rapidcheck >=2023.4,<2024; matching linux-64 entries are present in pixi.lock.

Remaining proof: restore the Pixi environment to run cmake --version and ninja --version, and document the CMake/build.rs ownership split.

Restore attempt (2026-10-03): pixi was not on PATH. scripts/restore.sh fetched origin/sandbox/developer-linux-64 and staged the transport, but failed before installing environments because the embedded pixi-sandbox launcher requires the missing .pixi-sandbox/tools/linux-64/trampoline_configuration/pixi-sandbox.json. The payload contains pixi 0.81.0, pixi-unpack, and pixi-sandbox, but no usable standalone pixi-sandbox executable.

Fallback pixi global install of pixi-sandbox==0.5.0 was attempted with the transport pixi and failed after three TLS-handshake retries against conda-forge. AC #4 remains unchecked; no .pixi environment was restored.

2026-10-03: Restored the published sandbox transport with bash scripts/restore.sh using pixi-sandbox 0.5.2. The restore verified 7,189 blobs, materialized pixi 0.81.0, pixi-sandbox 0.5.2, and pixi-unpack 0.7.11, restored default and bun, and verified 75,727 entries per environment with 0 failures.

2026-10-03: Consumer proof for AC #3: publish sandbox run 37138912619 succeeded for main a4869d3, publishing sandbox/developer-linux-64 at 1288845e57c327e429ea8914714509de621749f5.

2026-10-03: Consumer proof for AC #4: pixi run -e default cmake --version reported 4.4.3 and ninja --version reported 1.13.2 after scripts/restore.sh.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
CMake and Ninja are declared in the C++ toolchain feature without replacing the existing Rust-consumer build.rs path. The linux-64 lock and published sandbox were verified on the restored consumer transport, and both tools resolve in the restored default environment.
<!-- SECTION:FINAL_SUMMARY:END -->
