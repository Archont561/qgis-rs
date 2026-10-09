//! The retired-name lint: what counts as a retired spelling, and what does not.

use rstest::rstest;
use xtask::lints::{is_retired_name_history, retired_names_in};

#[rstest]
#[case::the_old_bridge_package("npm install @qgis-sdk/bridge", "@qgis-sdk/bridge")]
#[case::the_old_bridge_directory("see ts-packages/qgis-sdk-bridge", "qgis-sdk-bridge")]
#[case::the_retired_npm_scope("require('@qgis-rs/node-linux-x64-gnu')", "@qgis-rs/")]
#[case::the_retired_pip_name("pip install qgis-rs", "pip install qgis-rs")]
#[case::the_retired_npm_name("npm install qgis-rs", "npm install qgis-rs")]
#[case::the_retired_python_import("import qgis_rs", "import qgis_rs")]
#[case::the_retired_command("run `qgis-plugin install`", "qgis-plugin")]
#[case::the_old_repository_path("https://github.com/Archont561/qgis-rs", "Archont561/qgis-rs")]
fn a_retired_spelling_is_reported(#[case] text: &str, #[case] expected: &str) {
    assert_eq!(retired_names_in(text), vec![expected]);
}

#[rstest]
#[case::the_concept_name_with_a_suffix("the qgis-plugin-sdk concept")]
#[case::the_concept_file_name("see qgis-plugin-ui.md")]
#[case::the_cpp_namespace("using qgis_rs::native_manager::compact_json;")]
#[case::the_current_package("npm install @archont561/qgis-node")]
#[case::the_current_repository("github.com/Archont561/qgis-rust")]
fn a_current_spelling_is_not_reported(#[case] text: &str) {
    assert!(retired_names_in(text).is_empty(), "{text} was reported");
}

#[rstest]
#[case::backlog("backlog/tasks/task-60.md", true)]
#[case::decisions(".knowledge/decisions/D13-rust-cli.md", true)]
#[case::the_log(".knowledge/log.md", true)]
#[case::the_changelog("CHANGELOG.md", true)]
#[case::a_lock_file("bun.lock", true)]
#[case::current_docs("docs/src/content/docs/cli/index.mdx", false)]
#[case::a_knowledge_note(".knowledge/release.md", false)]
fn history_is_exempt_and_current_text_is_checked(#[case] path: &str, #[case] exempt: bool) {
    assert_eq!(is_retired_name_history(path), exempt);
}

#[test]
fn a_spelling_that_contains_another_is_reported_for_both() {
    // "pip install qgis-rs-py" is a retired distribution name and also starts
    // with the retired pip name, so both are reported.
    assert_eq!(
        retired_names_in("pip install qgis-rs-py"),
        vec!["qgis-rs-py", "pip install qgis-rs"]
    );
}
