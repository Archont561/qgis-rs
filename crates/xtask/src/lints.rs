//! The checks that are not any one package's: the C++ format gate, the TOML
//! canonicality gate, the published-package contents check, and the one
//! environment repair a conda QGIS prefix needs.

use std::path::{Path, PathBuf};

use anyhow::{bail, Context, Result};

use crate::util::{cpp_sources, repo_root, run};

/// clang-format gate for the native manager.
///
/// With arguments it checks exactly those files — that is how lefthook passes
/// the staged ones — and with none it checks the whole native manager. Assumes it runs
/// inside the `default` pixi environment, which is where clang-tools lives.
pub fn check_cpp(files: &[String]) -> Result<()> {
    let paths: Vec<PathBuf> = if files.is_empty() {
        cpp_sources()
    } else {
        files.iter().map(PathBuf::from).collect()
    };
    if paths.is_empty() {
        println!("check-cpp: no C++ sources to check");
        return Ok(());
    }
    let mut args = vec!["--dry-run".to_string(), "--Werror".to_string()];
    args.extend(paths.iter().map(|path| path.display().to_string()));
    run("clang-format", args)
}

/// Write clang-format's output for the native manager.
///
/// The mirror of [`check_cpp`]: same sources, same discovery, but `-i` instead
/// of `--dry-run --Werror`. A separate verb rather than a flag on `check-cpp`
/// because lefthook wants the check form on staged files and `format` wants this
/// one on the whole tree.
pub fn format_cpp() -> Result<()> {
    let paths = cpp_sources();
    if paths.is_empty() {
        println!("format-cpp: no C++ sources to format");
        return Ok(());
    }
    let mut args = vec!["-i".to_string()];
    args.extend(paths.iter().map(|path| path.display().to_string()));
    run("clang-format", args)
}

/// The C++ the cargo build compiles, and therefore the only C++ the compile
/// database describes.
///
/// `cpp_sources` also walks the shim's GoogleTest suite, which CMake builds
/// and cargo does not. clang-tidy is driven by `compile_commands.json`, so
/// pointing it at a file that database has never heard of makes it fall back
/// to a guessed command line and fail on the first Qt include.
pub const COMPILED_CPP_DIR: &str = "crates/qgis-sys/src";

/// Run clang-tidy over the native-manager sources using the compile database
/// produced by `qgis-sys`'s build script.
///
/// The compile database is the source of truth for the QGIS and Qt include
/// paths. The only extra paths are the conda GCC headers needed by clang when
/// it parses the database's GCC command line; discovering those here avoids a
/// fragile shell `find | head | xargs` pipeline.
pub fn clang_tidy() -> Result<()> {
    let root = repo_root();
    let prefix = std::env::var("CONDA_PREFIX")
        .context("CONDA_PREFIX is not set — run this under `pixi run -e default`")?;
    let compilation_database = root.join("compile_commands.json");
    if !compilation_database.is_file() {
        bail!(
            "clang-tidy: no compile_commands.json — run `pixi run -e default cargo build -p qgis-sys` first"
        );
    }

    let sources: Vec<PathBuf> = cpp_sources()
        .into_iter()
        .filter(|path| path.extension().and_then(std::ffi::OsStr::to_str) == Some("cpp"))
        .filter(|path| path.starts_with(root.join(COMPILED_CPP_DIR)))
        .collect();
    if sources.is_empty() {
        bail!("clang-tidy: no .cpp sources in the qgis-sys shim");
    }

    let gcc_include = first_matching_file(&Path::new(&prefix).join("lib/gcc"), |path| {
        path.file_name() == Some(std::ffi::OsStr::new("stddef.h"))
    })
    .and_then(|path| path.parent().map(Path::to_path_buf))
    .context("clang-tidy: no stddef.h under $CONDA_PREFIX/lib/gcc")?;

    run(
        "clang-tidy",
        clang_tidy_arguments(&root, Path::new(&prefix), &gcc_include, &sources),
    )
}

/// Build the clang-tidy command line from the compile database and the
/// compiler's conda-specific standard-library directories.
///
/// Kept as a pure seam so tests can pin the argument contract without starting
/// clang-tidy. `-p` makes clang-tidy consume `compile_commands.json`; the
/// database owns the native-manager and Qt include paths, while these extra
/// arguments make clang use the same conda C++ headers as the build.
pub fn clang_tidy_arguments(
    compilation_database: &Path,
    prefix: &Path,
    gcc_include: &Path,
    sources: &[PathBuf],
) -> Vec<String> {
    let sysroot = prefix.join("x86_64-conda-linux-gnu/sysroot");
    let cxx_include = gcc_include.join("c++");
    let target_cxx_include = cxx_include.join("x86_64-conda-linux-gnu");
    let backward_cxx_include = cxx_include.join("backward");
    let mut args = vec!["-p".to_string(), compilation_database.display().to_string()];
    args.extend(sources.iter().map(|path| path.display().to_string()));
    args.extend([
        "--quiet".to_string(),
        "--header-filter=^/.*/crates/qgis-sys/src/native_manager/.*".to_string(),
        format!("--extra-arg=--sysroot={}", sysroot.display()),
        format!("--extra-arg=-I{}", gcc_include.display()),
        "--extra-arg=-nostdinc++".to_string(),
        format!("--extra-arg=-isystem{}", cxx_include.display()),
        format!("--extra-arg=-isystem{}", target_cxx_include.display()),
        format!("--extra-arg=-isystem{}", backward_cxx_include.display()),
    ]);
    args
}

/// The lexicographically first file under `root` that `accepts`.
///
/// Sorted before the first is taken, so the answer does not depend on directory
/// iteration order: a lint that picks a different header directory on a
/// different machine is a lint whose failures nobody can reproduce. Public
/// because `tests/lints.rs` asserts that ordering on a tree it builds itself.
pub fn first_matching_file(root: &Path, accepts: impl Fn(&Path) -> bool) -> Option<PathBuf> {
    first_matching_entry(root, |path| path.is_file() && accepts(path))
}

fn first_matching_entry(root: &Path, accepts: impl Fn(&Path) -> bool) -> Option<PathBuf> {
    let mut matches: Vec<PathBuf> = walkdir::WalkDir::new(root)
        .into_iter()
        .filter_map(std::result::Result::ok)
        .map(walkdir::DirEntry::into_path)
        .filter(|path| accepts(path))
        .collect();
    matches.sort();
    matches.into_iter().next()
}

/// The manifests kept in taplo's canonical form.
///
/// Only this one is: the rest of the repository uses the aligned-`=` style
/// on purpose, and running taplo over them would rewrite a deliberate choice.
/// Public for `tests/lints.rs`, which asserts the file still exists.
pub const CANONICAL_TOML: &[&str] = &["pixi.toml"];

/// taplo canonicality check. Arguments (staged files) override the list above.
pub fn lint_toml(files: &[String]) -> Result<()> {
    let targets: Vec<String> = if files.is_empty() {
        CANONICAL_TOML.iter().map(ToString::to_string).collect()
    } else {
        files.to_vec()
    };
    let mut args = vec!["fmt".to_string(), "--check".to_string()];
    args.extend(targets);
    run("taplo", args)
}

/// Assert a package directory contains everything its `files` list promises,
/// before `npm publish` finds out for us in a way that cannot be unpublished.
///
/// An entry ending in `/` is checked as a directory; an entry containing `*`
/// is checked as a glob that must match at least once.
pub fn pack_check(package_dir: &str, required: &[String]) -> Result<()> {
    let directory = repo_root().join(package_dir);
    if !directory.is_dir() {
        bail!("no such package directory: {}", directory.display());
    }

    let mut missing = Vec::new();
    for entry in required {
        let present = if let Some(name) = entry.strip_suffix('/') {
            directory.join(name).is_dir()
        } else if entry.contains('*') {
            glob_matches(&directory, entry)?
        } else {
            directory.join(entry).exists()
        };
        if !present {
            missing.push(entry.clone());
        }
    }

    if !missing.is_empty() {
        for entry in &missing {
            eprintln!("missing from package: {entry} (did the build run?)");
        }
        bail!("{} entries missing from {package_dir}", missing.len());
    }
    println!("package contents verified in {package_dir}");
    Ok(())
}

/// Whether at least one file matches a `*`-pattern inside `directory`.
///
/// Only the forms the packages actually use are supported — one `*` in the
/// file-name part, optionally under a subdirectory (`qgis-node.*.node`,
/// `dist/*.whl`) — which is why this is twenty lines instead of a glob
/// dependency nobody else in the workspace needs.
pub fn glob_matches(directory: &Path, pattern: &str) -> Result<bool> {
    let (sub_directory, file_pattern) = match pattern.rsplit_once('/') {
        Some((parent, name)) => (directory.join(parent), name),
        None => (directory.to_path_buf(), pattern),
    };
    let (prefix, suffix) = file_pattern
        .split_once('*')
        .context("a glob needs exactly one '*' in its file name")?;
    let Ok(entries) = std::fs::read_dir(&sub_directory) else {
        // A missing directory is a missing match, not an error: that is
        // exactly what this check reports on.
        return Ok(false);
    };
    for entry in entries {
        let name = entry?.file_name().to_string_lossy().into_owned();
        if name.len() >= prefix.len() + suffix.len()
            && name.starts_with(prefix)
            && name.ends_with(suffix)
        {
            return Ok(true);
        }
    }
    Ok(false)
}

/// The trees that hold hand-written source, as opposed to build output.
///
/// Public for `tests/lints.rs`: which directories count as source is the whole
/// content of [`check_sources`].
pub const SOURCE_TREES: &[&str] = &["crates", "py-packages", "ts-packages", "scripts"];

/// Directory segments inside those trees that are *not* source.
const BUILD_OUTPUT: &[&str] = &[
    "node_modules/",
    "__pycache__/",
    "/dist/",
    "/build/",
    "/target/",
    "/.pixi/",
    "/.venv/",
];

/// File extensions a reader would call source.
const SOURCE_EXTENSIONS: &[&str] = &[
    ".py", ".pyi", ".rs", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".cpp", ".h", ".hpp",
];

/// Whether `path` is a source file that belongs in the repository.
///
/// Dot-prefixed names are excluded: a generated `.napi-generated.d.ts` sits
/// next to the addon it describes and is ignored on purpose. Public because
/// this predicate, not the git plumbing around it, is what the test pins.
#[must_use]
pub fn looks_like_source(path: &str) -> bool {
    let name = path.rsplit('/').next().unwrap_or(path);
    if name.starts_with('.') {
        return false;
    }
    if BUILD_OUTPUT.iter().any(|segment| path.contains(segment)) {
        return false;
    }
    SOURCE_EXTENSIONS
        .iter()
        .any(|extension| name.ends_with(extension))
}

/// Fail if a source file inside a package tree is ignored by git.
///
/// This exists because it already happened: `.gitignore` ignores `_*` so that
/// build droppings stay out, re-included a list of Python module names by
/// hand, and the day `_api.py` and `_transport.py` were written nobody
/// remembered to extend the list. Both files were real source, both were
/// invisible to `git status`, and the whole Python client was pushed as a
/// package that could not import itself — a local gate that ran against the
/// files on disk said nothing, because on disk they were there.
///
/// An ignored file that is *not* source — a wheel, an addon, a generated
/// `.d.ts` — is exactly what the ignore rules are for and is not reported.
pub fn check_sources() -> Result<()> {
    let root = repo_root();
    if !root.join(".git").exists() {
        println!("check-sources: not a git checkout, nothing to compare");
        return Ok(());
    }

    let mut args = vec![
        "ls-files".to_string(),
        "--others".to_string(),
        "--ignored".to_string(),
        "--exclude-standard".to_string(),
        "--".to_string(),
    ];
    args.extend(SOURCE_TREES.iter().map(ToString::to_string));
    let listed = crate::util::capture("git", args)?;
    if !listed.status.success() {
        bail!(
            "git ls-files failed: {}",
            String::from_utf8_lossy(&listed.stderr)
        );
    }

    let hidden: Vec<&str> = std::str::from_utf8(&listed.stdout)
        .context("git listed a path that is not UTF-8")?
        .lines()
        .filter(|path| looks_like_source(path))
        .collect();

    if !hidden.is_empty() {
        for path in &hidden {
            eprintln!("ignored but looks like source: {path}");
        }
        bail!(
            "{} source file(s) are hidden by .gitignore — commit them, or narrow the ignore rule",
            hidden.len()
        );
    }
    println!(
        "check-sources: every source file in {} trees is visible to git",
        SOURCE_TREES.len()
    );
    check_retired_names()
}

/// Outcome of checking the QCA soname required by QGIS.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum QcaRepair {
    /// The package already supplied the expected file or link.
    NothingToRepair,
    /// A missing or incorrect link was replaced.
    Repaired,
}

/// Ensure one library directory contains the Qt5 soname QGIS dlopens.
///
/// Public for `tests/lints.rs`, which builds isolated package layouts and
/// verifies that a correct installation is not rewritten.
pub fn setup_qca_in(lib: &Path) -> Result<QcaRepair> {
    let target = lib.join("libqca-qt5.so.2");
    let source = if lib.join("libqca-qt6.so.2").exists() {
        lib.join("libqca-qt6.so.2")
    } else if lib.join("libqca-qt5.so.2.3.12").exists() {
        lib.join("libqca-qt5.so.2.3.12")
    } else {
        bail!("no libqca found under {}", lib.display());
    };

    if target.is_file() && !target.is_symlink() {
        return Ok(QcaRepair::NothingToRepair);
    }
    if target.is_symlink() && std::fs::read_link(&target).ok().as_ref() == Some(&source) {
        return Ok(QcaRepair::NothingToRepair);
    }
    if target.exists() || target.is_symlink() {
        std::fs::remove_file(&target)
            .with_context(|| format!("cannot replace {}", target.display()))?;
    }
    std::os::unix::fs::symlink(&source, &target)
        .with_context(|| format!("cannot link {} -> {}", target.display(), source.display()))?;
    Ok(QcaRepair::Repaired)
}

/// Repair QCA in the active pixi prefix when the restored package needs it.
pub fn setup_qca() -> Result<()> {
    let prefix = std::env::var("CONDA_PREFIX")
        .context("CONDA_PREFIX is not set — run this under `pixi run -e default`")?;
    let lib = Path::new(&prefix).join("lib");
    match setup_qca_in(&lib)? {
        QcaRepair::NothingToRepair => println!("setup-qca: nothing to repair"),
        QcaRepair::Repaired => println!(
            "setup-qca: repaired {}",
            lib.join("libqca-qt5.so.2").display()
        ),
    }
    Ok(())
}

/// Names that were renamed or removed and must not come back in tracked text.
///
/// Each is a spelling the project no longer ships: the bridge package before
/// TASK-56, the `qgis-rs-py` distribution before the `qgis-py` rename, the
/// `qgis-rs` npm and pip names that TASK-58 and the Python rename retired, and
/// the Python `qgis_rs` import shim, and the old repository path (the repository
/// is `qgis-rust`; `qgis-rs` remains the crate API name). The C++ namespace of the native manager was `qgis_rs::`; it is
/// `qgis_sys::` now, and the old spelling is listed so it cannot return.
pub const RETIRED_NAMES: &[&str] = &[
    "@qgis-sdk/bridge",
    "qgis-sdk-bridge",
    "qgis-rs-py",
    "@qgis-rs/",
    "pip install qgis-rs",
    "npm install qgis-rs",
    "import qgis_rs",
    "from qgis_rs",
    "Archont561/qgis-rs",
    "qgis_rs::native_manager",
];

/// The retired `qgis-plugin` command. It is matched as a whole token, so a longer
/// name that merely starts with it is not a hit.
pub const RETIRED_COMMAND: &str = "qgis-plugin";

/// Tracked text that may name a retired spelling on purpose: history, and the
/// rule itself with its tests (which must spell the names they forbid).
pub fn is_retired_name_history(path: &str) -> bool {
    path.starts_with("backlog/")
        || path.starts_with(".knowledge/decisions/")
        || path == ".knowledge/log.md"
        || path == "CHANGELOG.md"
        || path.ends_with(".lock")
        || path == "crates/xtask/src/lints.rs"
        || path == "crates/xtask/src/boundaries.rs"
        || path == "crates/xtask/tests/boundaries.rs"
        || path == "crates/xtask/tests/retired_names.rs"
}

/// Every retired spelling that `text` contains, in the order of [`RETIRED_NAMES`],
/// followed by [`RETIRED_COMMAND`] when it appears as a whole token.
pub fn retired_names_in(text: &str) -> Vec<&'static str> {
    let mut hits: Vec<&'static str> = RETIRED_NAMES
        .iter()
        .copied()
        .filter(|name| text.contains(name))
        .collect();
    let bounded =
        |byte: Option<char>| byte.is_none_or(|c| !(c.is_alphanumeric() || c == '-' || c == '_'));
    let mut from = 0;
    while let Some(offset) = text[from..].find(RETIRED_COMMAND) {
        let start = from + offset;
        let end = start + RETIRED_COMMAND.len();
        let before = text[..start].chars().next_back();
        let after = text[end..].chars().next();
        if bounded(before) && bounded(after) {
            hits.push(RETIRED_COMMAND);
            break;
        }
        from = end;
    }
    hits
}

/// Fail when a tracked file, outside the history allowlist, still spells a
/// retired name. Runs inside [`check_sources`], so it is part of `pixi run gates`.
pub fn check_retired_names() -> Result<()> {
    let root = repo_root();
    if !root.join(".git").exists() {
        return Ok(());
    }
    let listed = crate::util::capture("git", ["ls-files".to_string()])?;
    if !listed.status.success() {
        bail!(
            "git ls-files failed: {}",
            String::from_utf8_lossy(&listed.stderr)
        );
    }
    let mut offenders = Vec::new();
    for path in std::str::from_utf8(&listed.stdout)
        .context("git listed a path that is not UTF-8")?
        .lines()
    {
        if is_retired_name_history(path) {
            continue;
        }
        let Ok(text) = std::fs::read_to_string(root.join(path)) else {
            continue;
        };
        for name in retired_names_in(&text) {
            offenders.push(format!("{path}: {name}"));
        }
    }
    if !offenders.is_empty() {
        for offender in &offenders {
            eprintln!("retired name: {offender}");
        }
        bail!(
            "{} retired name(s) in tracked files — use the current name, or record history in the backlog or .knowledge/log.md",
            offenders.len()
        );
    }
    println!("check-sources: no retired names in tracked files");
    Ok(())
}
