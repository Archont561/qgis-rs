---
id: TASK-24
title: Add cmake and ninja to the C++ toolchain dependencies
status: To Do
assignee: []
created_date: '2026-10-02 23:22'
labels:
  - build
  - cpp
  - tooling
dependencies: []
references:
  - 'https://github.com/Archont561/qgis-rs/issues/19'
priority: medium
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The C++ side of the repository has no build system of its own. Every .cpp under crates/qgis-sys/src is compiled by build.rs through the cc and cxx-build crates, straight into the Rust link line, and build.rs hand-writes compile_commands.json afterwards so clangd and clang-tidy have something to read.

That is enough while the only consumer of the shim is rustc, and it stops being enough twice:

- TASK-23 asks for a GoogleTest + RapidCheck suite for the shim. cc and cxx-build produce static archives for a Rust crate; they cannot produce a standalone test executable, and a test target that links libqgis_core plus Qt needs real target modelling (include dirs, rpath, Qt moc-free headers, QT_QPA_PLATFORM=offscreen at run time).
- RFC #19 (issue 19) proposes a single C-ABI manager translation unit exported as a shared library with -fvisibility=hidden and exactly three default-visible symbols. That is a link-level artifact with its own symbol policy, which cc cannot express.

Both point at the same missing pair of tools: cmake to describe the C++ targets and ninja to run them. Declare them where the other C++ tooling already lives, in [feature.cxx.dependencies] next to cxx-compiler and clang-tools.

Two facts found while checking the current environment:

- Neither cmake nor ninja is in pixi.lock or in .pixi/envs/default; only /usr/bin/make exists, from the base image.
- GoogleTest is already in the environment (include/gtest/gtest.h, lib/libgtest.so.1.16.0, lib/libgmock.so.1.16.0) but nothing in pixi.lock or conda-meta declares it: those files are shipped by the minizip-4.2.2 conda package. Relying on that is relying on a packaging accident, so gtest has to be declared too. RapidCheck is absent; conda-forge/rapidcheck-feedstock exists, so it can be declared the same way.

Note on how this has to be landed: conda-forge is unreachable from the dev sandbox (the repodata fetch returns no response), so pixi add cannot re-solve the lock here. The solve has to run on a GitHub runner, and the sandbox pack has to be republished afterwards, or a restored sandbox will still not have the binaries.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 cmake and ninja are declared in [feature.cxx.dependencies] in pixi.toml with upper-bounded version ranges
- [ ] #2 gtest is declared explicitly instead of being inherited from the minizip package, and rapidcheck is declared or TASK-23 records why it is vendored instead
- [ ] #3 pixi.lock is regenerated for linux-64 on a runner, since conda-forge cannot be reached from the sandbox, and the sandbox pack is republished so a restored environment contains the new tools
- [ ] #4 cmake --version and ninja --version resolve inside the default pixi environment after scripts/restore.sh
- [ ] #5 A short note in CONTEXT.md or the README records which parts of the C++ build cmake owns and that build.rs still owns the shim compiled into qgis-sys
<!-- AC:END -->
