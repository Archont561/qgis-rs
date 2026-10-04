//! The three things every subcommand needs: where the repository is, how to
//! run a program in it, and how to announce a step.

use std::ffi::OsStr;
use std::path::{Path, PathBuf};
use std::process::{Command, Output, Stdio};

use anyhow::{bail, Context, Result};

/// The repository root.
///
/// Derived from this crate's own manifest directory rather than from
/// `git rev-parse`, so the answer is the same whether xtask was started by a
/// pixi task, by turbo from inside a package, by lefthook, or by a person in a
/// random subdirectory — and so it still works in a tree that is not a git
/// checkout (a release tarball, a container layer).
#[must_use]
pub fn repo_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(2)
        .expect("crates/xtask is two levels below the repository root")
        .to_path_buf()
}

/// Print a step header, in the same shape the shell gate used.
pub fn step(message: &str) {
    println!("\n\x1b[1m── {message}\x1b[0m");
}

/// Run a program at the repository root, inheriting stdio, and fail if it does.
pub fn run<I, S>(program: &str, args: I) -> Result<()>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    run_in(&repo_root(), program, args)
}

/// Run a program in `directory`, inheriting stdio.
pub fn run_in<I, S>(directory: &Path, program: &str, args: I) -> Result<()>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    let args: Vec<String> = args
        .into_iter()
        .map(|arg| arg.as_ref().to_string_lossy().into_owned())
        .collect();
    let status = Command::new(program)
        .args(&args)
        .current_dir(directory)
        .status()
        .with_context(|| format!("cannot start {program}"))?;
    if !status.success() {
        bail!("{program} {} failed with {status}", args.join(" "));
    }
    Ok(())
}

/// Run a program and capture what it wrote, without failing on a non-zero exit.
///
/// Used where the *output* is the decision — `cargo publish` rejecting an
/// upload that already exists, `git diff` reporting drift.
pub fn capture<I, S>(program: &str, args: I) -> Result<Output>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    Command::new(program)
        .args(args)
        .current_dir(repo_root())
        .stdin(Stdio::null())
        .output()
        .with_context(|| format!("cannot start {program}"))
}

/// Run a pixi task or command in one of the two environments.
///
/// Everything that touches QGIS, Python or the C++ toolchain runs in
/// `default`; everything that touches JavaScript runs in `bun`. The split is
/// forced by an icu conflict — see the header of pixi.toml.
pub fn pixi<I, S>(environment: &str, args: I) -> Result<()>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    let mut full = vec!["run".to_string(), "-e".to_string(), environment.to_string()];
    full.extend(
        args.into_iter()
            .map(|arg| arg.as_ref().to_string_lossy().into_owned()),
    );
    run("pixi", full)
}

/// Run a pixi command with one environment variable set on the pixi process.
///
/// Public for the local gate: setting `CARGO_NET_OFFLINE` inside the target
/// command is too late because napi starts Cargo through another process.
pub fn pixi_with_env<I, S>(environment: &str, args: I, key: &str, value: &str) -> Result<()>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    let args: Vec<String> = args
        .into_iter()
        .map(|arg| arg.as_ref().to_string_lossy().into_owned())
        .collect();
    let status = Command::new("pixi")
        .args(["run", "-e", environment, "--"])
        .args(&args)
        .env(key, value)
        .current_dir(repo_root())
        .status()
        .context("cannot start pixi")?;
    if !status.success() {
        bail!(
            "pixi run -e {environment} -- {} failed with {status}",
            args.join(" ")
        );
    }
    Ok(())
}

/// Every C++ source and header in the qgis-sys shim, sorted.
///
/// Sorted because an unsorted walk makes clang-format's output order depend on
/// the filesystem, and a gate that reports its findings in a different order
/// on every machine is a gate nobody diffs.
#[must_use]
pub fn cpp_sources() -> Vec<PathBuf> {
    let root = repo_root();
    let mut files: Vec<PathBuf> = ["crates/qgis-sys/src", "crates/qgis-sys/include"]
        .iter()
        .flat_map(|directory| walkdir::WalkDir::new(root.join(directory)))
        .filter_map(std::result::Result::ok)
        .filter(|entry| entry.file_type().is_file())
        .map(walkdir::DirEntry::into_path)
        .filter(|path| {
            matches!(
                path.extension().and_then(std::ffi::OsStr::to_str),
                Some("cpp" | "h")
            )
        })
        .collect();
    files.sort();
    files
}
