//! End-to-end tests for the `qgis-cli` binary itself.
//!
//! Every test needs the same two things — a way to invoke the binary and a
//! scratch directory to point it at — so both come from one `cli` fixture
//! instead of the five free functions (`run`, `temp_dir`, `write_project`,
//! `stdout_of`, `stderr_of`) this file used to open with. The fixture also
//! removes its directory on drop, which the hand-rolled version never did.

use std::path::{Path, PathBuf};
use std::process::Command;

use rstest::{fixture, rstest};

const BINARY: &str = env!("CARGO_BIN_EXE_qgis-cli");

/// One CLI invocation, already decoded.
///
/// Holding `stdout`/`stderr` as `String` is what retired `stdout_of` and
/// `stderr_of`: a test asserts on `run.stdout` directly, and a failure message
/// can print `run.stderr` without converting it again.
struct Run {
    status: std::process::ExitStatus,
    stdout: String,
    stderr: String,
}

impl Run {
    fn succeeded(&self) -> bool {
        self.status.success()
    }
}

/// The binary under test, plus a scratch directory of its own.
struct Cli {
    dir: PathBuf,
}

impl Cli {
    fn new() -> Self {
        // Unique per test: the previous fixed names (`qgis-cli-it-dry-run`
        // and friends) were shared state between concurrent runs.
        let unique = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .expect("system clock is after the epoch")
            .as_nanos();
        let dir = std::env::temp_dir().join(format!("qgis-cli-it-{unique}"));
        std::fs::create_dir_all(&dir).expect("create dir");
        Self { dir }
    }

    /// Run the CLI and capture everything.
    fn run(&self, args: &[&str]) -> Run {
        let output = Command::new(BINARY)
            .args(args)
            .output()
            .unwrap_or_else(|error| panic!("run `qgis-cli {}`: {error}", args.join(" ")));
        Run {
            status: output.status,
            stdout: String::from_utf8_lossy(&output.stdout).into_owned(),
            stderr: String::from_utf8_lossy(&output.stderr).into_owned(),
        }
    }

    /// Write a minimal project file into the scratch directory.
    fn project(&self, name: &str) -> PathBuf {
        let path = self.dir.join(name);
        std::fs::write(&path, b"<qgis></qgis>").expect("write project");
        path
    }

    /// A path inside the scratch directory, as the CLI wants it: `&str`.
    fn path(&self, name: &str) -> String {
        utf8(&self.dir.join(name))
    }
}

impl Drop for Cli {
    fn drop(&mut self) {
        std::fs::remove_dir_all(&self.dir).ok();
    }
}

#[fixture]
fn cli() -> Cli {
    Cli::new()
}

fn utf8(path: &Path) -> String {
    path.to_str().expect("utf-8").to_owned()
}

#[rstest]
fn version_reports_the_crate_version(cli: Cli) {
    let run = cli.run(&["--version"]);
    assert!(run.succeeded(), "{}", run.stderr);
    assert!(run.stdout.contains(env!("CARGO_PKG_VERSION")));
}

#[rstest]
#[case("render")]
#[case("tiles")]
#[case("batch")]
#[case("info")]
#[case("serve")]
#[case("export")]
fn help_lists_every_subcommand(cli: Cli, #[case] command: &str) {
    let run = cli.run(&["--help"]);
    assert!(run.succeeded(), "{}", run.stderr);
    assert!(
        run.stdout.contains(command),
        "{command} missing from: {}",
        run.stdout
    );
}

#[rstest]
fn a_dry_run_counts_tiles_without_rendering(cli: Cli) {
    let project = cli.project("map.qgs");

    let run = cli.run(&[
        "tiles",
        &utf8(&project),
        "-z",
        "10-14",
        "-b",
        "14,50,15,51",
        "-o",
        &cli.path("tiles"),
        "--dry-run",
    ]);
    assert!(run.succeeded(), "{}", run.stderr);

    assert!(
        run.stdout.contains("Would render 4568 tiles"),
        "{}",
        run.stdout
    );
    assert!(run.stdout.contains("z=10"), "{}", run.stdout);
    assert!(run.stdout.contains("24 tiles"), "{}", run.stdout);
}

/// The legacy dry-run report, pinned whole rather than by substring.
///
/// `plan tiles` prints the same per-level rows, so a format change here would
/// quietly change two commands' output. Pinning the exact text says which
/// command owns the wording, and that this one still says "Would render".
#[rstest]
fn the_legacy_dry_run_report_is_unchanged(cli: Cli) {
    let project = cli.project("map.qgs");

    let run = cli.run(&[
        "tiles",
        &utf8(&project),
        "-z",
        "10-14",
        "-b",
        "14,50,15,51",
        "-o",
        &cli.path("tiles"),
        "--dry-run",
    ]);

    assert_eq!(
        run.stdout,
        "z=10  x 551..554  y 342..347  24 tiles\n\
         z=11  x 1103..1109  y 685..694  70 tiles\n\
         z=12  x 2207..2218  y 1371..1389  228 tiles\n\
         z=13  x 4414..4437  y 2742..2778  888 tiles\n\
         z=14  x 8829..8874  y 5484..5556  3358 tiles\n\
         Would render 4568 tiles across zoom levels 10-14\n",
        "{}",
        run.stderr
    );
}

#[rstest]
fn info_prints_json_without_needing_qgis(cli: Cli) {
    let project = cli.project("map.qgz");

    let run = cli.run(&["info", &utf8(&project), "--json"]);
    assert!(run.succeeded(), "{}", run.stderr);

    let parsed: serde_json::Value = serde_json::from_str(&run.stdout).expect("valid json");
    assert!(run.stderr.is_empty());
    assert_eq!(
        parsed,
        serde_json::json!({
            "path": project, "format": "qgz", "size_bytes": 13,
            "crs": null, "layer_count": null, "extent": null,
            "note": "CRS, layer count and extent are only available through the native QGIS backend project reader"
        })
    );
}

#[rstest]
fn operations_that_need_qgis_say_so(cli: Cli) {
    let project = cli.project("map.qgs");
    let target = cli.path("out.png");

    let run = cli.run(&["render", &utf8(&project), "-o", &target]);
    assert!(!run.succeeded());
    assert!(run.stderr.contains("QGIS backend"), "{}", run.stderr);
    assert!(
        !Path::new(&target).exists(),
        "nothing should have been written"
    );
}

#[rstest]
fn a_missing_project_is_reported_with_its_path(cli: Cli) {
    let path = cli.path("missing.qgs");
    for args in [vec!["info", &path], vec!["info", &path, "--json"]] {
        let run = cli.run(&args);
        assert_eq!(run.status.code(), Some(1));
        assert!(run.stdout.is_empty());
        assert!(run.stderr.contains("project not found"), "{}", run.stderr);
        assert!(run.stderr.contains(&path), "{}", run.stderr);
    }
}

#[rstest]
fn legacy_info_keeps_its_human_report(cli: Cli) {
    let project = cli.project("map.qgs");
    let run = cli.run(&["info", &utf8(&project)]);
    assert_eq!(run.status.code(), Some(0));
    assert!(run.stderr.is_empty());
    assert_eq!(run.stdout, format!(
        "path:    {}\nformat:  qgs\nsize:    13 bytes\ncrs:     unknown\nlayers:  unknown\nnote:    CRS, layer count and extent are only available through the native QGIS backend project reader\n",
        project.display()
    ));
}

#[rstest]
fn serve_needs_a_project_or_a_directory(cli: Cli) {
    let run = cli.run(&["serve"]);
    assert!(!run.succeeded());
    assert!(run.stderr.contains("--projects-dir"), "{}", run.stderr);
}

#[rstest]
fn batch_reads_the_extents_csv_before_failing(cli: Cli) {
    let project = cli.project("map.qgs");
    let extents = cli.path("extents.csv");
    std::fs::write(
        &extents,
        "name,minx,miny,maxx,maxy\nberlin,13.08,52.33,13.76,52.68\n",
    )
    .expect("write csv");

    let run = cli.run(&[
        "batch",
        &utf8(&project),
        "--extents",
        &extents,
        "-o",
        &cli.path("renders"),
    ]);
    assert!(!run.succeeded());

    assert!(
        run.stdout.contains("berlin: 13.08,52.33,13.76,52.68"),
        "{}",
        run.stdout
    );
    assert!(run.stderr.contains("QGIS backend"));
}

#[rstest]
fn an_unknown_subcommand_is_a_usage_error(cli: Cli) {
    let run = cli.run(&["teleport"]);
    assert!(!run.succeeded());
    assert!(run.stderr.contains("unrecognized subcommand"));
}
