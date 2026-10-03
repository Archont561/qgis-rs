//! The checks that are not any one package's: the C++ format gate, the TOML
//! canonicality gate, the published-package contents check, and the one
//! environment repair a conda QGIS prefix needs.

use std::path::{Path, PathBuf};

use anyhow::{bail, Context, Result};

use crate::util::{cpp_sources, repo_root, run};

/// clang-format gate for the C++ shim.
///
/// With arguments it checks exactly those files — that is how lefthook passes
/// the staged ones — and with none it checks the whole shim. Assumes it runs
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

/// Write clang-format's output for the C++ shim.
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

/// clang-tidy over the C++ shim, with the include paths it needs discovered.
///
/// This is the one lint that could not be a manifest one-liner while it lived in
/// a shell file: clang-tidy parses the shim against the real headers, and every
/// path it needs is version-stamped or content-hashed — the cxxbridge out-dir
/// under `target/debug/build/qgis-sys-*/out`, Qt under `include/qt` or
/// `include/qt6` depending on the build, and the GCC internal include directory
/// carrying `stddef.h`. Discovering them in Rust rather than in
/// `find | head | xargs` is what lets `@qgis/rust`'s `lint` script be a single
/// line, and it makes a missing directory a named error instead of an empty
/// argument list.
pub fn clang_tidy() -> Result<()> {
    let prefix = std::env::var("CONDA_PREFIX")
        .context("CONDA_PREFIX is not set — run this under `pixi run -e default`")?;

    let sources: Vec<PathBuf> = cpp_sources()
        .into_iter()
        .filter(|path| path.extension().and_then(std::ffi::OsStr::to_str) == Some("cpp"))
        .collect();
    if sources.is_empty() {
        bail!("clang-tidy: no .cpp sources in the qgis-sys shim");
    }

    let qt_include = ["include/qt", "include/qt6"]
        .iter()
        .map(|candidate| Path::new(&prefix).join(candidate))
        .find(|candidate| candidate.is_dir())
        .with_context(|| {
            format!("clang-tidy: no Qt headers under {prefix}/include — qt or include/qt6 missing?")
        })?;

    // target/debug/build/qgis-sys-<hash>/out/cxxbridge — a *directory*, which is
    // why this is not the same walk as the stddef.h hunt below. The two are
    // sorted, so a workspace that carries several feature configurations of the
    // shim gets the same include directory on every machine rather than whichever
    // one `find` happened to list first.
    let cxx_out = first_matching_dir(&repo_root().join("target/debug/build"), |path| {
        path.file_name() == Some(std::ffi::OsStr::new("cxxbridge"))
            && path
                .parent()
                .and_then(Path::file_name)
                .is_some_and(|name| name == "out")
            && path
                .parent()
                .and_then(Path::parent)
                .and_then(Path::file_name)
                .is_some_and(|name| name.to_string_lossy().starts_with("qgis-sys-"))
    })
    .context(
        "clang-tidy: no cxxbridge output under target/debug/build — run \
         `pixi run -e default cargo build -p qgis-sys` first",
    )?;

    let gcc_include = first_matching_file(&Path::new(&prefix).join("lib/gcc"), |path| {
        path.file_name() == Some(std::ffi::OsStr::new("stddef.h"))
    })
    .and_then(|path| path.parent().map(Path::to_path_buf))
    .context("clang-tidy: no stddef.h under $CONDA_PREFIX/lib/gcc")?;

    run(
        "clang-tidy",
        clang_tidy_arguments(
            &repo_root().join("crates/qgis-sys"),
            Path::new(&prefix),
            &qt_include,
            &cxx_out,
            &gcc_include,
            &sources,
        ),
    )
}

/// The clang-tidy command line for the shim, from five discovered directories.
///
/// Split out from [`clang_tidy`] so the part that can be wrong — the order of
/// the arguments — is a pure function a test can pin, instead of something only
/// observable by running clang-tidy against a built QGIS.
///
/// Every path is absolute. The shell version this replaced `cd crates` first and
/// passed `-Iqgis-sys` relative to that; a subcommand runs at the repository
/// root, where the same two flags name a directory that does not exist, so the
/// shim is passed in rather than assumed to be underfoot.
pub fn clang_tidy_arguments(
    shim: &Path,
    prefix: &Path,
    qt_include: &Path,
    cxx_out: &Path,
    gcc_include: &Path,
    sources: &[PathBuf],
) -> Vec<String> {
    let sysroot = prefix.join("x86_64-conda-linux-gnu/sysroot");
    let mut args: Vec<String> = sources
        .iter()
        .map(|path| path.display().to_string())
        .collect();
    // The sources must come BEFORE the `--` separator; everything after it is
    // the compiler command line. Passing them the other way round — which is
    // what piping them through `xargs` after the separator did — makes
    // clang-tidy print its own --help and exit 123.
    args.push(format!("--extra-arg=--sysroot={}", sysroot.display()));
    args.push(format!("--extra-arg=-I{}", gcc_include.display()));
    args.push("--".to_string());
    args.extend([
        "-std=c++17".to_string(),
        format!("-I{}", shim.display()),
        format!("-I{}/include", shim.display()),
        format!("-I{}/include", cxx_out.display()),
        format!("-I{}/crate", cxx_out.display()),
        format!("-I{}/include/qgis", prefix.display()),
        format!("-I{}", qt_include.display()),
        format!("-I{}/QtCore", qt_include.display()),
        format!("-I{}/QtGui", qt_include.display()),
        format!("-I{}/QtWidgets", qt_include.display()),
        format!("-I{}/QtXml", qt_include.display()),
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

/// [`first_matching_file`] for directories.
fn first_matching_dir(root: &Path, accepts: impl Fn(&Path) -> bool) -> Option<PathBuf> {
    first_matching_entry(root, |path| path.is_dir() && accepts(path))
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
/// file-name part, optionally under a subdirectory (`qgis-rs.*.node`,
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
    Ok(())
}

/// Link libqca under the Qt5 soname QGIS still dlopens, whichever flavour
/// conda-forge installed. Idempotent, so every task that needs a live QGIS can
/// call it unconditionally.
pub fn setup_qca() -> Result<()> {
    let prefix = std::env::var("CONDA_PREFIX")
        .context("CONDA_PREFIX is not set — run this under `pixi run -e default`")?;
    let lib = Path::new(&prefix).join("lib");
    let target = lib.join("libqca-qt5.so.2");

    let source = if lib.join("libqca-qt6.so.2").exists() {
        lib.join("libqca-qt6.so.2")
    } else if lib.join("libqca-qt5.so.2.3.12").exists() {
        lib.join("libqca-qt5.so.2.3.12")
    } else {
        bail!("no libqca found under {}", lib.display());
    };

    // Replace rather than fail: the link may point at a library from a prefix
    // that has since been rebuilt.
    if target.exists() || target.is_symlink() {
        std::fs::remove_file(&target)
            .with_context(|| format!("cannot replace {}", target.display()))?;
    }
    std::os::unix::fs::symlink(&source, &target)
        .with_context(|| format!("cannot link {} -> {}", target.display(), source.display()))?;
    println!("{} -> {}", target.display(), source.display());
    Ok(())
}
