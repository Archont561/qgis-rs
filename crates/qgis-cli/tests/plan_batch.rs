//! Pure batch planning through argv, streams, exit status and filesystem effects.
use std::path::PathBuf;
use std::process::{Command, Output};

use rstest::{fixture, rstest};
use serde_json::{json, Value};

struct Sandbox {
    path: PathBuf,
}

impl Sandbox {
    fn new() -> Self {
        let unique = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path =
            std::env::temp_dir().join(format!("qgis-plan-batch-{}-{unique}", std::process::id()));
        std::fs::create_dir(&path).unwrap();
        Self { path }
    }

    fn write(&self, bytes: &[u8]) {
        std::fs::write(self.path.join("extents.csv"), bytes).unwrap();
    }

    fn run(&self, args: &[&str]) -> Output {
        Command::new(env!("CARGO_BIN_EXE_qgis-cli"))
            .args(args)
            .current_dir(&self.path)
            .env("PATH", "")
            .env("HOME", self.path.join("home"))
            .env("XDG_CONFIG_HOME", self.path.join("config"))
            .env("XDG_CACHE_HOME", self.path.join("cache"))
            .env("QT_QPA_PLATFORM", "offscreen")
            .output()
            .expect("run CLI without helper runtimes")
    }

    fn entries(&self) -> Vec<String> {
        let mut entries: Vec<_> = std::fs::read_dir(&self.path)
            .unwrap()
            .map(|entry| entry.unwrap().file_name().into_string().unwrap())
            .collect();
        entries.sort();
        entries
    }
}

impl Drop for Sandbox {
    fn drop(&mut self) {
        std::fs::remove_dir_all(&self.path).unwrap();
    }
}

#[fixture]
fn sandbox() -> Sandbox {
    Sandbox::new()
}

const FLAGS: &[&str] = &["plan", "batch", "--extents", "extents.csv", "-z", "10-14"];
const CSV: &[u8] = b"name,minx,miny,maxx,maxy\nfirst,14,50,15,51\nsecond,14,50,15,51\n";

fn json_report(output: &Output) -> Value {
    serde_json::from_slice(&output.stdout).expect("one JSON report on stdout")
}

fn golden_plan() -> Value {
    json!({
        "bounds": {"min_x": 14.0, "min_y": 50.0, "max_x": 15.0, "max_y": 51.0},
        "zooms": {"min": 10, "max": 14},
        "tile_count": 4568,
        "levels": [
            {"zoom": 10, "x_min": 551, "x_max": 554, "y_min": 342, "y_max": 347, "tile_count": 24},
            {"zoom": 11, "x_min": 1103, "x_max": 1109, "y_min": 685, "y_max": 694, "tile_count": 70},
            {"zoom": 12, "x_min": 2207, "x_max": 2218, "y_min": 1371, "y_max": 1389, "tile_count": 228},
            {"zoom": 13, "x_min": 4414, "x_max": 4437, "y_min": 2742, "y_max": 2778, "tile_count": 888},
            {"zoom": 14, "x_min": 8829, "x_max": 8874, "y_min": 5484, "y_max": 5556, "tile_count": 3358}
        ]
    })
}

#[rstest]
fn batch_json_embeds_the_shared_plan_without_opening_a_project(sandbox: Sandbox) {
    sandbox.write(CSV);
    let output = sandbox.run(&[FLAGS, &["--json"]].concat());

    assert_eq!(output.status.code(), Some(0), "{output:?}");
    assert!(output.stderr.is_empty(), "{output:?}");
    let report = json_report(&output);
    assert_eq!(
        report,
        json!({
            "extent_count": 2,
            "tile_count": 9136,
            "extents": [
                {"name": "first", "plan": golden_plan()},
                {"name": "second", "plan": golden_plan()}
            ]
        })
    );
    let engine = qgis_engine::call(
        qgis_engine::Operation::PlanTiles,
        json!({"bounds": "14,50,15,51", "zooms": "10-14"}),
    );
    assert!(engine.ok);
    assert_eq!(report["extents"][0]["plan"], engine.result);
    assert_eq!(sandbox.entries(), ["extents.csv"]);
    assert_eq!(
        std::fs::read(sandbox.path.join("extents.csv")).unwrap(),
        CSV
    );
}

#[rstest]
fn the_human_report_names_each_plan_without_claiming_to_render(sandbox: Sandbox) {
    sandbox.write(CSV);
    let output = sandbox.run(FLAGS);

    assert_eq!(output.status.code(), Some(0), "{output:?}");
    assert!(output.stderr.is_empty());
    assert_eq!(
        String::from_utf8(output.stdout).unwrap(),
        "first: 4568 tiles across zoom levels 10-14\n\
         second: 4568 tiles across zoom levels 10-14\n\
         9136 tiles across 2 extents\n"
    );
    assert_eq!(sandbox.entries(), ["extents.csv"]);
}

#[rstest]
#[case::too_few_columns(b"bad,14,50\n")]
#[case::not_a_number(b"bad,14,50,15,x\n")]
#[case::reversed_bounds(b"bad,15,51,14,50\n")]
#[case::nan(b"bad,NaN,50,15,51\n")]
#[case::infinity(b"bad,14,50,inf,51\n")]
#[case::invalid_utf8(b"\xff\n")]
fn malformed_csv_fails_atomically_with_exit_ten(sandbox: Sandbox, #[case] bad_row: &[u8]) {
    let mut csv = b"name,minx,miny,maxx,maxy\nvalid,14,50,15,51\n".to_vec();
    csv.extend_from_slice(bad_row);
    sandbox.write(&csv);
    let output = sandbox.run(&[FLAGS, &["--json"]].concat());

    assert_eq!(output.status.code(), Some(10), "{output:?}");
    let report = json_report(&output);
    assert_eq!(report["error"]["code"], "invalid_input");
    assert_eq!(report.as_object().unwrap().len(), 1, "no partial plans");
    let message = report["error"]["message"].as_str().unwrap();
    assert!(String::from_utf8_lossy(&output.stderr).contains(message));
    if bad_row.is_ascii() {
        assert!(message.contains("line 3"), "{message}");
    }
    let human = sandbox.run(FLAGS);
    assert_eq!(human.status.code(), Some(10));
    assert!(human.stdout.is_empty());
    assert_eq!(human.stderr, output.stderr);
    assert_eq!(sandbox.entries(), ["extents.csv"]);
    assert_eq!(
        std::fs::read(sandbox.path.join("extents.csv")).unwrap(),
        csv
    );
}

fn assert_failure(sandbox: &Sandbox, flags: &[&str], exit: i32, code: &str) {
    let output = sandbox.run(&[flags, &["--json"]].concat());
    assert_eq!(output.status.code(), Some(exit), "{output:?}");
    let report = json_report(&output);
    assert_eq!(report["error"]["code"], code);
    assert_eq!(report.as_object().unwrap().len(), 1, "no partial plans");
    let message = report["error"]["message"].as_str().unwrap();
    assert!(!message.is_empty());
    assert!(String::from_utf8_lossy(&output.stderr).contains(message));
    let human = sandbox.run(flags);
    assert_eq!(human.status.code(), Some(exit));
    assert!(human.stdout.is_empty());
    assert_eq!(human.stderr, output.stderr);
}

#[rstest]
fn a_missing_csv_has_exit_eleven_not_a_domain_error(sandbox: Sandbox) {
    assert_failure(&sandbox, FLAGS, 11, "missing_input");
    assert_eq!(sandbox.entries(), Vec::<String>::new());
}

#[rstest]
fn a_directory_is_rejected_before_it_can_be_read_as_csv(sandbox: Sandbox) {
    std::fs::create_dir(sandbox.path.join("extents.csv")).unwrap();
    assert_failure(&sandbox, FLAGS, 10, "invalid_input");
    assert_eq!(sandbox.entries(), ["extents.csv"]);
}

#[cfg(unix)]
#[rstest]
fn a_symlink_loop_has_exit_fourteen_not_a_missing_or_invalid_input(sandbox: Sandbox) {
    std::os::unix::fs::symlink("extents.csv", sandbox.path.join("extents.csv")).unwrap();
    assert_failure(&sandbox, FLAGS, 14, "filesystem_failure");
    assert_eq!(sandbox.entries(), ["extents.csv"]);
    assert_eq!(
        std::fs::read_link(sandbox.path.join("extents.csv")).unwrap(),
        PathBuf::from("extents.csv")
    );
}

#[rstest]
fn repeated_plans_preserve_order_unicode_duplicate_and_empty_names(sandbox: Sandbox) {
    let csv = "# comment\nNAME,minx,miny,maxx,maxy\n same , 14,50,15,51\nŻółć,14,50,15,51,ignored\nname,header,inside,the,file\nsame,14,50,15,51\n,14,50,15,51\n";
    sandbox.write(csv.as_bytes());
    let first = sandbox.run(&[FLAGS, &["--json"]].concat());
    let second = sandbox.run(&[FLAGS, &["--json"]].concat());

    assert_eq!(first.status.code(), Some(0), "{first:?}");
    assert_eq!(second.status.code(), Some(0), "{second:?}");
    assert!(first.stderr.is_empty());
    assert!(second.stderr.is_empty());
    assert_eq!(first.stdout, second.stdout);
    assert_eq!(
        json_report(&first),
        json!({
            "extent_count": 4,
            "tile_count": 18272,
            "extents": [
                {"name": "same", "plan": golden_plan()},
                {"name": "Żółć", "plan": golden_plan()},
                {"name": "same", "plan": golden_plan()},
                {"name": "", "plan": golden_plan()}
            ]
        })
    );
    assert_eq!(sandbox.entries(), ["extents.csv"]);
    assert_eq!(
        std::fs::read(sandbox.path.join("extents.csv")).unwrap(),
        csv.as_bytes()
    );
}

#[rstest]
#[case::empty(b"")]
#[case::headers_and_comments(b"# comment\n\nNaMe,minx,miny,maxx,maxy\n")]
fn a_csv_without_extents_is_a_valid_zero_work_plan(sandbox: Sandbox, #[case] csv: &[u8]) {
    sandbox.write(csv);
    let output = sandbox.run(&[FLAGS, &["--json"]].concat());
    assert_eq!(output.status.code(), Some(0), "{output:?}");
    assert!(output.stderr.is_empty());
    assert_eq!(
        json_report(&output),
        json!({"extent_count": 0, "tile_count": 0, "extents": []})
    );
    let human = sandbox.run(FLAGS);
    assert_eq!(human.status.code(), Some(0));
    assert!(human.stderr.is_empty());
    assert_eq!(human.stdout, b"0 tiles across 0 extents\n");
    assert_eq!(sandbox.entries(), ["extents.csv"]);
}

#[rstest]
#[case::too_deep("99")]
#[case::reversed("14-10")]
#[case::not_a_zoom("ten")]
fn invalid_zoom_is_reported_as_exit_ten(sandbox: Sandbox, #[case] zoom: &str) {
    sandbox.write(CSV);
    assert_failure(
        &sandbox,
        &["plan", "batch", "--extents", "extents.csv", "--zoom", zoom],
        10,
        "invalid_input",
    );
    assert_eq!(sandbox.entries(), ["extents.csv"]);
}

#[rstest]
#[case::missing_csv(&["plan", "batch", "-z", "10"])]
#[case::missing_zoom(&["plan", "batch", "--extents", "extents.csv"])]
#[case::legacy_output(&["plan", "batch", "--extents", "extents.csv", "-z", "10", "--output", "renders"])]
fn usage_errors_keep_exit_two_and_do_not_write(sandbox: Sandbox, #[case] args: &[&str]) {
    let output = sandbox.run(&[args, &["--json"]].concat());
    assert_eq!(output.status.code(), Some(2), "{output:?}");
    assert!(output.stdout.is_empty());
    assert!(!output.stderr.is_empty());
    assert_eq!(sandbox.entries(), Vec::<String>::new());
}
