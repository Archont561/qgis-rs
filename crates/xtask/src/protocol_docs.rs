//! The wire-protocol reference page, checked against the protocol itself.
//!
//! [D09](../../../.knowledge/decisions/D09-wire-protocol-over-ffi.md) makes one
//! JSON envelope the interface every binding speaks, so the docs site needs a
//! page describing it. A hand-written page listing twenty-nine operations and
//! sixteen error kinds is also a second copy of two lists that already exist
//! in `qgis-protocol`, and the usual fate of a second copy is to be right on
//! the day it is written and wrong a month later.
//!
//! So the page is written by hand — prose about an envelope is worth writing —
//! but which *names* it contains is not a matter of opinion. This module links
//! `qgis-protocol` and compares the published tables against
//! [`Operation::all`] and [`ErrorKind::all`] in both directions: a kind the
//! engine serves and the page omits is a violation, and so is a kind the page
//! invents. The Python column is checked against the mapping in the Python
//! client's own source rather than a list kept here, because a gate carrying
//! its own copy of the thing it is checking would simply certify the drift.
//!
//! The page marks its machine-checked regions with MDX comments
//! (`{/* protocol-docs:operations:begin */}`), which keeps the prose around
//! them free to change without touching this module.

use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Path, PathBuf};

use anyhow::{bail, Context, Result};
use qgis_protocol::{ErrorKind, Operation, TRANSPORT_VERSION};

/// Repository-relative path of the page this gate owns.
pub const PAGE: &str = "docs/src/content/docs/reference/wire-protocol.mdx";

/// Repository-relative path of the Python client whose exception mapping the
/// published error table has to agree with.
pub const PYTHON_TRANSPORT: &str = "py-packages/qgis-py/python/qgis_py/_transport.py";

/// The exception a kind maps to when the Python client lists no better one.
///
/// `_EXCEPTION_BY_KIND` only names the kinds that deserve something more
/// specific than "the engine refused these values", which is what `ValueError`
/// — and therefore `InvalidInput` — already means.
pub const PYTHON_FALLBACK_EXCEPTION: &str = "InvalidInput";

/// Where the JavaScript client renames the wire's `snake_case` to camelCase.
pub const JS_RENAME_EDGE: &str = "ts-packages/qgis-node/src/index.js";

/// The one error class the JavaScript client throws, whatever the kind.
const JS_ERROR_CLASS: &str = "EngineError";

/// The repository root, derived from this crate's manifest.
///
/// Public so `tests/protocol_docs.rs` can run the gate over the real tree
/// without shelling out to git.
#[must_use]
pub fn repo_root_from_manifest() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .to_path_buf()
}

/// The `kind -> exception class` mapping the Python client implements.
///
/// Parsed out of `_EXCEPTION_BY_KIND` rather than duplicated, so the gate
/// compares the documentation against the code that will actually run.
#[must_use]
pub fn python_exception_by_kind(source: &str) -> BTreeMap<String, String> {
    let mut mapping = BTreeMap::new();
    let Some(start) = source.find("_EXCEPTION_BY_KIND") else {
        return mapping;
    };
    let rest = &source[start..];
    let Some(open) = rest.find('{') else {
        return mapping;
    };
    let Some(close) = rest[open..].find('}') else {
        return mapping;
    };

    for line in rest[open + 1..open + close].lines() {
        let line = line.trim().trim_end_matches(',');
        let Some((key, value)) = line.split_once(':') else {
            continue;
        };
        let key = key.trim().trim_matches(['"', '\'']);
        let value = value.trim();
        if key.is_empty() || value.is_empty() {
            continue;
        }
        mapping.insert(key.to_string(), value.to_string());
    }
    mapping
}

/// Everything wrong with `page`, in reading order. Empty means the page is
/// consistent with the protocol it documents.
#[must_use]
pub fn violations(page: &str, python: &BTreeMap<String, String>) -> Vec<String> {
    let mut found = Vec::new();

    check_transport_version(page, &mut found);
    check_operations(page, &mut found);
    check_error_kinds(page, python, &mut found);

    if !page.contains("snake_case") {
        found.push(
            "the page must state the snake_case-on-the-wire rule, and it does not mention \
             snake_case at all"
                .to_string(),
        );
    }
    if !page.contains(JS_RENAME_EDGE) {
        found.push(format!(
            "the page must say where the JavaScript client renames to camelCase — name \
             {JS_RENAME_EDGE}"
        ));
    }

    found
}

fn check_transport_version(page: &str, found: &mut Vec<String>) {
    let Some(block) = block(page, "transport-version") else {
        found.push(
            "the transport-version block is missing; the page has to state which envelope \
             version it documents"
                .to_string(),
        );
        return;
    };

    let expected = TRANSPORT_VERSION.to_string();
    let states_it = block
        .split(|character: char| !character.is_ascii_digit())
        .any(|token| token == expected);
    if !states_it {
        found.push(format!(
            "the transport-version block does not state transport version {TRANSPORT_VERSION}, \
             which is what this build speaks"
        ));
    }
}

fn check_operations(page: &str, found: &mut Vec<String>) {
    let Some(block) = block(page, "operations") else {
        found.push(
            "the operations block is missing; without it the page documents no operations and \
             nothing would notice"
                .to_string(),
        );
        return;
    };

    let documented = first_column(block);
    let served: BTreeSet<&str> = Operation::all().iter().copied().collect();

    for name in &served {
        if !documented.contains(*name) {
            found.push(format!(
                "operation `{name}` is served by the engine but has no row in the operations table"
            ));
        }
    }
    for name in &documented {
        if !served.contains(name.as_str()) {
            found.push(format!(
                "operation `{name}` is documented but is not an Operation variant"
            ));
        }
    }
}

fn check_error_kinds(page: &str, python: &BTreeMap<String, String>, found: &mut Vec<String>) {
    let Some(block) = block(page, "errors") else {
        found.push(
            "the errors block is missing; the page has to carry the ErrorKind table".to_string(),
        );
        return;
    };

    let rows: BTreeMap<String, Vec<String>> = data_rows(block)
        .into_iter()
        .filter_map(|cells| Some((code_span(cells.first()?)?, cells)))
        .collect();
    let served: BTreeSet<&str> = ErrorKind::all().iter().map(|kind| kind.as_str()).collect();

    for kind in &served {
        let Some(cells) = rows.get(*kind) else {
            found.push(format!(
                "error kind `{kind}` is in ErrorKind but has no row in the error table"
            ));
            continue;
        };

        let expected = python
            .get(*kind)
            .map_or(PYTHON_FALLBACK_EXCEPTION, String::as_str);
        match cells.get(1).and_then(|cell| code_span(cell)) {
            Some(documented) if documented == expected => {}
            Some(documented) => found.push(format!(
                "error kind `{kind}` becomes `{expected}` in {PYTHON_TRANSPORT}, but the table \
                 says `{documented}`"
            )),
            None => found.push(format!(
                "error kind `{kind}` has no Python exception in its row; every kind becomes \
                 `{expected}`"
            )),
        }

        let javascript = cells.get(2).map_or("", String::as_str);
        if !javascript.contains(JS_ERROR_CLASS) {
            found.push(format!(
                "error kind `{kind}` must reach JavaScript as {JS_ERROR_CLASS}, but its row does \
                 not say so"
            ));
        }
    }

    for kind in rows.keys() {
        if !served.contains(kind.as_str()) {
            found.push(format!(
                "error kind `{kind}` is documented but is not an ErrorKind variant"
            ));
        }
    }
}

/// The text between a marked region's `begin` and `end` comments.
fn block<'a>(page: &'a str, name: &str) -> Option<&'a str> {
    let begin = format!("{{/* protocol-docs:{name}:begin */}}");
    let end = format!("{{/* protocol-docs:{name}:end */}}");
    let start = page.find(&begin)? + begin.len();
    let stop = page[start..].find(&end)? + start;
    Some(&page[start..stop])
}

/// The inline-code span a cell leads with, if it has one.
fn code_span(cell: &str) -> Option<String> {
    let rest = cell.split_once('`')?.1;
    let (inner, _) = rest.split_once('`')?;
    (!inner.is_empty()).then(|| inner.to_string())
}

/// Every table row's cells, skipping headers and separators — which is any
/// line whose first cell carries no inline-code span.
fn data_rows(block: &str) -> Vec<Vec<String>> {
    block
        .lines()
        .map(str::trim)
        .filter(|line| line.starts_with('|'))
        .map(|line| {
            line.trim_matches('|')
                .split('|')
                .map(|cell| cell.trim().to_string())
                .collect::<Vec<_>>()
        })
        .filter(|cells| cells.first().and_then(|cell| code_span(cell)).is_some())
        .collect()
}

/// The leading code span of every data row.
fn first_column(block: &str) -> BTreeSet<String> {
    data_rows(block)
        .into_iter()
        .filter_map(|cells| code_span(cells.first()?))
        .collect()
}

/// Check the published page against the protocol.
///
/// # Errors
///
/// Fails with every violation listed, so one run names all the drift rather
/// than the first instance of it.
pub fn run(repo_root: &Path) -> Result<()> {
    let page_path = repo_root.join(PAGE);
    let page = fs::read_to_string(&page_path)
        .with_context(|| format!("cannot read the wire-protocol page {}", page_path.display()))?;

    let python_path = repo_root.join(PYTHON_TRANSPORT);
    let python_source = fs::read_to_string(&python_path)
        .with_context(|| format!("cannot read the Python client {}", python_path.display()))?;
    let mapping = python_exception_by_kind(&python_source);

    let violations = violations(&page, &mapping);
    if violations.is_empty() {
        println!(
            "wire-protocol page documents {} operations and {} error kinds",
            Operation::all().len(),
            ErrorKind::all().len()
        );
        return Ok(());
    }

    for violation in &violations {
        eprintln!("  {violation}");
    }
    bail!(
        "{} is out of step with qgis-protocol ({} problem(s))",
        PAGE,
        violations.len()
    )
}
