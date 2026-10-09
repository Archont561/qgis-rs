//! The D13 product boundaries: what the rules reject, what the parsers read,
//! and the one assertion that matters most — this repository obeys them.

use rstest::{fixture, rstest};
use xtask::boundaries::{
    check, parse_crate, parse_distribution, read_tree, violations, CrateFacts, DistributionFacts,
    Tree, BINDING_CRATES, CANONICAL_BINARIES, FORBIDDEN_EDGES, TRACKED_FALLBACKS,
};
use xtask::util::repo_root;

/// A tree that satisfies every rule, to mutate one fact at a time.
#[fixture]
fn lawful_tree() -> Tree {
    Tree {
        crates: vec![
            CrateFacts {
                name: "qgis-cli".into(),
                dependencies: vec!["qgis-render".into()],
                binaries: vec!["qgis-cli".into()],
            },
            CrateFacts {
                name: "qgis-py".into(),
                dependencies: vec!["qgis-engine".into()],
                binaries: vec![],
            },
            CrateFacts {
                name: "qgis-node".into(),
                dependencies: vec!["qgis-engine".into()],
                binaries: vec![],
            },
            CrateFacts {
                name: "qgis-server".into(),
                dependencies: vec!["qgis-engine".into()],
                binaries: vec![],
            },
        ],
        distributions: vec![DistributionFacts {
            name: "qgis-sdk".into(),
            dependencies: vec![],
        }],
        fallbacks: TRACKED_FALLBACKS
            .iter()
            .map(|(path, _)| (*path).to_string())
            .collect(),
    }
}

#[rstest]
fn a_lawful_tree_has_nothing_to_report(lawful_tree: Tree) {
    assert_eq!(violations(&lawful_tree), vec![]);
}

/// The single-violation rules, as one case each.
///
/// Every one of these used to be its own copy of "take the lawful tree, break
/// exactly one fact, expect exactly one violation". The break is the case
/// datum — a non-capturing closure coerced to `fn(&mut Tree)` — so adding a
/// rule means adding a line, not another near-identical test.
#[rstest]
#[case::an_executable_with_two_owners_names_both(
    |tree: &mut Tree| tree.crates[3].binaries.push("qgis-cli".into()),
    "canonical executables",
    "qgis-cli, qgis-server"
)]
#[case::a_retired_executable_that_comes_back_is_a_violation(
    |tree: &mut Tree| tree.crates[0].binaries.push("qgis-plugin".into()),
    "canonical executables",
    "qgis-plugin"
)]
#[case::a_canonical_executable_that_disappears(
    |tree: &mut Tree| tree.crates[0].binaries.clear(),
    "canonical executables",
    "no crate declares qgis-cli"
)]
#[case::a_new_fallback_fails(
    |tree: &mut Tree| tree.fallbacks.push("ts-packages/qgis-node/src/fallback.js".into()),
    "no new fallbacks",
    "untracked fallback"
)]
fn breaking_one_fact_reports_exactly_one_violation(
    mut lawful_tree: Tree,
    #[case] break_one_fact: fn(&mut Tree),
    #[case] rule: &str,
    #[case] detail: &str,
) {
    break_one_fact(&mut lawful_tree);

    let found = violations(&lawful_tree);
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0].rule, rule);
    assert!(found[0].detail.contains(detail), "{found:?}");
}

#[rstest]
fn a_binding_crate_that_grows_a_binary_is_a_violation(mut lawful_tree: Tree) {
    lawful_tree.crates[2].binaries.push("qgis-cli".into());

    let rules: Vec<&str> = violations(&lawful_tree)
        .iter()
        .map(|found| found.rule)
        .collect();
    // Two rules break at once, and both are worth printing: the binding crate
    // owns a binary, and two crates now claim the same executable.
    assert!(
        rules.contains(&"binding crates own no binaries"),
        "{rules:?}"
    );
    assert!(rules.contains(&"canonical executables"), "{rules:?}");
}

#[test]
fn the_cargo_parser_reads_the_three_facts_it_needs() {
    let facts = parse_crate(
        r#"
# A comment that mentions name = "not-this"
[package]
name = "qgis-sdk"
version.workspace = true

[lib]
name = "qgis_sdk_core"

[[bin]]
name = "qgis-sdk"
path = "src/bin/qgis-sdk.rs"

[dependencies]
anyhow = { workspace = true }
qgis-cli = { workspace = true }

[features]
default = ["python"]
"#,
    );

    assert_eq!(facts.name, "qgis-sdk");
    assert_eq!(facts.binaries, vec!["qgis-sdk"]);
    assert_eq!(facts.dependencies, vec!["anyhow", "qgis-cli"]);
    // `[lib] name` and `[features] default` are not dependencies or binaries.
    assert!(!facts.dependencies.contains(&"default".to_string()));
}

#[test]
fn the_pyproject_parser_reads_both_spellings_of_dependencies() {
    let inline = parse_distribution("[project]\nname = \"qgis-sdk\"\ndependencies = []\n");
    assert_eq!(inline.name, "qgis-sdk");
    assert_eq!(inline.dependencies, Vec::<String>::new());

    let multiline = parse_distribution(
        "[project]\nname = \"qgis-rs\"\ndependencies = [\n  \"typing-extensions\",\n]\n\n[project.scripts]\nqgis-cli = \"qgis_py.cli:main\"\n",
    );
    assert_eq!(multiline.name, "qgis-rs");
    assert_eq!(multiline.dependencies, vec!["typing-extensions"]);
}

/// qgis-sdk is a pure-Python distribution, so its Rust crates are retired. The
/// directories must be gone and the workspace must not name them, or cargo
/// would keep building a CLI nothing ships.
#[test]
fn the_qgis_sdk_rust_crates_are_retired() {
    let root = repo_root();

    for dir in ["crates/qgis-sdk", "crates/qgis-sdk-core"] {
        assert!(!root.join(dir).exists(), "{dir} must be removed");
    }
    let manifest = std::fs::read_to_string(root.join("Cargo.toml")).expect("workspace manifest");
    assert!(!manifest.contains("crates/qgis-sdk"), "{manifest}");
}

#[test]
fn this_repository_obeys_its_own_contract() {
    check(&repo_root()).expect("the manifests match D13");
}

/// The rules are only as good as the tree they read: if discovery stops
/// finding the crates the contract names, every rule passes vacuously.
#[test]
fn the_tree_discovery_finds_the_crates_and_distributions_the_rules_name() {
    let tree = read_tree(&repo_root()).expect("readable manifests");

    for (crate_name, _, _) in FORBIDDEN_EDGES {
        assert!(
            tree.crates.iter().any(|facts| facts.name == *crate_name),
            "{crate_name} is not in the discovered tree"
        );
    }
    for binding in BINDING_CRATES {
        assert!(
            tree.crates.iter().any(|facts| facts.name == *binding),
            "{binding} is not in the discovered tree"
        );
    }
    for (_, owner) in CANONICAL_BINARIES {
        assert!(
            tree.crates.iter().any(|facts| facts.name == *owner),
            "{owner} is not in the discovered tree"
        );
    }
    assert!(
        tree.distributions
            .iter()
            .any(|facts| facts.name == "qgis-sdk"),
        "the hosted distribution is not in the discovered tree"
    );
}
