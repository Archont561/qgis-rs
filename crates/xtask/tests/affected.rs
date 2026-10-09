use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

use rstest::{fixture, rstest};
use xtask::affected::{changed_paths, plan, Scope};

#[fixture]
fn repo() -> PathBuf {
    let root = std::env::temp_dir().join(format!("qgis-rs-affected-{}", std::process::id()));
    let _ = fs::remove_dir_all(&root);
    for (path, body) in [
        ("crates/core/Cargo.toml", "[package]\nname = \"core\"\n"),
        ("crates/app/Cargo.toml", "[package]\nname = \"app\"\n"),
        ("ts-packages/web/package.json", r#"{"name":"@qgis/web"}"#),
        ("py-packages/sdk/package.json", r#"{"name":"sdk-py"}"#),
        ("docs/package.json", r#"{"name":"docs"}"#),
        (
            "py-packages/qgis-py/src-rust/Cargo.toml",
            "[package]\nname = \"qgis-py\"\n",
        ),
    ] {
        let path = root.join(path);
        fs::create_dir_all(path.parent().unwrap()).unwrap();
        fs::write(path, body).unwrap();
    }
    root
}

#[rstest]
#[case("crates/core/src/lib.rs", Scope::Rust("core".into()))]
#[case("ts-packages/web/src/index.ts", Scope::Package("@qgis/web".into()))]
#[case("py-packages/sdk/tests/test_api.py", Scope::Package("sdk-py".into()))]
#[case("docs/src/content/docs/index.mdx", Scope::Package("docs".into()))]
// A binding crate lives beside its language package, but its change is a Cargo
// change: the Rust scope, not the package.json scope of py-packages/qgis-py.
#[case("py-packages/qgis-py/src-rust/src/lib.rs", Scope::Rust("qgis-py".into()))]
fn a_leaf_change_selects_its_owner(repo: PathBuf, #[case] changed: &str, #[case] expected: Scope) {
    let result = plan(&repo, &[PathBuf::from(changed)], false).unwrap();
    assert_eq!(result.scopes, [expected]);
    assert!(!result.full_gate);
}

#[rstest]
#[case("Cargo.lock")]
#[case("turbo.json")]
#[case("test-fixtures/bridge/cases.json")]
#[case("crates/xtask/src/ci.rs")]
fn shared_inputs_select_the_full_gate(repo: PathBuf, #[case] changed: &str) {
    let result = plan(&repo, &[PathBuf::from(changed)], false).unwrap();
    assert!(
        result.full_gate,
        "{changed} must conservatively run the gate"
    );
    assert!(result.scopes.is_empty());
}

#[test]
fn clean_tree_has_no_work() {
    let root = std::env::temp_dir();
    let result = plan(&root, &[], false).unwrap();
    assert!(!result.full_gate);
    assert!(result.scopes.is_empty());
    assert!(result.commands.is_empty());
}

#[rstest]
fn duplicate_and_deleted_paths_produce_one_deterministic_command(repo: PathBuf) {
    let changed = [
        PathBuf::from("crates/core/deleted.rs"),
        PathBuf::from("crates/core/src/lib.rs"),
    ];
    let result = plan(&repo, &changed, true).unwrap();
    assert_eq!(result.scopes, [Scope::Rust("core".into())]);
    assert_eq!(result.commands.len(), 1);
    assert!(result.commands[0].display().contains("rdeps(core)"));
}

#[test]
fn explicit_base_collects_committed_renamed_deleted_and_untracked_paths() {
    let root = std::env::temp_dir().join(format!("qgis-rs-affected-git-{}", std::process::id()));
    let _ = fs::remove_dir_all(&root);
    fs::create_dir_all(root.join("crates/core/src")).unwrap();
    fs::write(root.join("crates/core/src/old.rs"), "old").unwrap();
    fs::write(root.join("crates/core/src/delete.rs"), "delete").unwrap();
    git(&root, &["init"]);
    git(&root, &["config", "user.email", "tests@example.invalid"]);
    git(&root, &["config", "user.name", "Tests"]);
    git(&root, &["add", "."]);
    git(&root, &["commit", "-m", "base"]);
    git(&root, &["tag", "base"]);
    git(
        &root,
        &["mv", "crates/core/src/old.rs", "crates/core/src/new.rs"],
    );
    fs::remove_file(root.join("crates/core/src/delete.rs")).unwrap();
    fs::write(root.join("crates/core/src/untracked.rs"), "new").unwrap();

    let paths = changed_paths(&root, Some("base")).unwrap();
    assert_eq!(
        paths,
        [
            PathBuf::from("crates/core/src/delete.rs"),
            PathBuf::from("crates/core/src/new.rs"),
            PathBuf::from("crates/core/src/untracked.rs"),
        ]
    );
}

fn git(root: &Path, args: &[&str]) {
    assert!(Command::new("git")
        .args(args)
        .current_dir(root)
        .status()
        .unwrap()
        .success());
}

#[test]
fn fixture_paths_are_relative() {
    assert!(Path::new("crates/core/src/lib.rs").is_relative());
}
