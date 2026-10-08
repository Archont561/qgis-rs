//! Discover every public declaration in the manifest's source headers.
//!
//! The manifest is reviewed data: a human decides that `QgsVectorLayer::fields`
//! is `supported_manual` and which operation serves it. This module is the
//! mechanical half — it asks clang what the declared headers actually contain
//! and records the answer, so a declaration cannot enter or leave the reviewed
//! surface without the gate saying so (TASK-30 AC#1, doc-4 gate 2).
//!
//! # What is discovered
//!
//! One [`Discovery`] per public declaration in a header the manifest's
//! `source.headers` names:
//!
//! * every *definition* of a class in a declared header contributes its
//!   **public** members — methods, constructors, destructors, conversions,
//!   fields, nested classes, enums, static data members and typedefs;
//! * a nested class is discovered under its qualified scope
//!   (`QgsVectorLayer::LayerOptions`), so ids never collide across scopes;
//! * functions, variables, enums and typedefs declared at file or namespace
//!   scope in a declared header are discovered too.
//!
//! Out of scope by policy, not by accident: template declarations, `friend`
//! declarations (the friend's own declaration is discovered where it is
//! declared), using-directives, and anything clang marks implicit — the
//! compiler's own copy constructors and assignments, template instantiations,
//! and Qt's `Q_OBJECT` macro trampolines inside generated instantiations.
//! Widening the policy is a change to [`declared_kind`], and the inventory
//! records the policy identity it was written by ([`EXTRACTOR_ID`]).
//!
//! # How it is discovered
//!
//! `clang-check -ast-dump` over a generated translation unit that includes the
//! declared headers, in one pass, with the include contract `clang-tidy` uses:
//! the conda GCC headers, the sysroot and `-nostdinc++`, because a probe that
//! picks up the *system* libstdc++ does not compile, and a dump that does not
//! compile is not an inventory. Extraction requires a clean exit: an error
//! diagnostic fails it rather than silently shortening it.
//!
//! The dump is text — `clang-check` refuses `-ast-dump=json` (TASK-30's
//! 2026-10-07 note) — so the parser models the two things the text encodes: a
//! tree by the two-character prefix on each line (`|-`, `` `- ``), and a
//! location that omits its file name whenever it repeats the last one printed.
//! `tests/api_extract.rs` pins that model on hand-written dumps.
//!
//! # What the inventory says
//!
//! [`classify`] gives every discovered declaration one of the manifest's
//! statuses, a reason and a version range, and leaves none of them empty:
//!
//! | discovered as | status | reason |
//! | --- | --- | --- |
//! | a declaration the manifest reviews | the manifest's status | the manifest's reason |
//! | marked deprecated in the headers | `deprecated` | [`REASON_DEPRECATED`] |
//! | anything else | `unsupported` | [`REASON_NOT_REVIEWED`] |
//!
//! The version range is the reviewed range for a reviewed declaration and the
//! manifest's own floor (`>=<min_version>,<4`) for every other one — the only
//! range the native manager can promise for a surface it has not reviewed.
//! `since` is the reviewed value or `unknown`: QGIS's `\since` doc comments are
//! in the dump, and deriving from them is a later slice rather than a guess.
//!
//! # What the gate checks
//!
//! [`verify_repository`] is the single verification the `check-api-inventory`
//! repo lint and `pixi run xtask api-extract --check` both run:
//!
//! 1. the checked-in inventory is byte-identical to a fresh extraction, so it
//!    cannot rot between upgrades;
//! 2. every declaration the manifest reviews is still discovered by name, so a
//!    reviewed declaration cannot outlive the header that declared it; and
//! 3. every entry carries a status, a reason and a version range, and ids are
//!    unique.

use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::Path;
use std::process::Command;

use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};

use crate::api_manifest::{validate_manifest, ApiManifest, MANIFEST_PATH};
use crate::lints::first_matching_file;
use crate::util::repo_root;

/// The generated inventory, beside the manifest it is checked against.
pub const INVENTORY_PATH: &str = "crates/qgis-sys/native_manager/generated/api_inventory.json";

/// The extractor's identity, recorded in the inventory it writes.
///
/// It names the policy — what [`parse_dump`] records and what it skips — so a
/// reader of an entry can tell which extractor produced it.
pub const EXTRACTOR_ID: &str = "clang-ast-text/public-members/v1";

/// The reason recorded for a declaration nobody has reviewed yet.
pub const REASON_NOT_REVIEWED: &str =
    "discovered by the header extractor; not yet reviewed against the headless manager contract";

/// The reason recorded for a declaration the headers mark deprecated.
pub const REASON_DEPRECATED: &str = "declared deprecated in the QGIS headers";

/// One public declaration discovered in the declared headers.
///
/// `id` is `Scope::name(params)` with parameter *types*; the manifest's own
/// reviewed ids spell parameter names where they exist, so the gate matches on
/// `Scope::name` and never on the parenthesised part.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct Discovery {
    /// `QgsVectorLayer::fields`, or `QgsVectorLayer::addFeature(QgsFeature&)`.
    pub id: String,
    /// One of the kinds [`declared_kind`] maps.
    pub kind: String,
    /// The header the declaration is written in, e.g. `qgsvectorlayer.h`.
    pub header: String,
    /// The owning class scope, empty for a file-scope declaration.
    pub scope: String,
    /// The member name without its scope, e.g. `addFeature`.
    pub member: String,
    /// Whether the AST carries a deprecation attribute for it.
    pub deprecated: bool,
}

/// One inventory entry: a discovered declaration plus its explicit support
/// decision. Every field is required — the gate rejects an empty one.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct InventoryEntry {
    /// `Scope::name(params)`.
    pub id: String,
    /// Declaration kind, as [`Discovery::kind`] spells it.
    pub kind: String,
    /// Declaring header.
    pub header: String,
    /// A status from the manifest's vocabulary.
    pub status: String,
    /// The first QGIS version the declaration appeared in, or `unknown`.
    pub since: String,
    /// The QGIS version range the manager accounts for.
    pub version_range: String,
    /// Why the declaration has that status.
    pub reason: String,
}

/// The generated inventory document.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Inventory {
    /// Extractor policy identity.
    pub extractor: String,
    /// The clang that produced the dump, e.g. `22.1.8`.
    pub clang_version: String,
    /// The manifest's QGIS pin, copied so an entry can be read alone.
    pub qgis_min_version: String,
    /// The manifest's tested QGIS version.
    pub qgis_tested_version: String,
    /// The declared headers this inventory extracted, in manifest order.
    pub headers: Vec<String>,
    /// How many entries carry each status — the table's one-line summary.
    pub counts: BTreeMap<String, usize>,
    /// Every discovered declaration, ordered by id.
    pub declarations: Vec<InventoryEntry>,
}

/// Split one dump line into its depth and node text.
///
/// The dump indents with two-character groups (`| ` or `  `) followed by a
/// branch marker; a node at depth `d` has `d` groups, and the translation unit
/// itself matches nothing, which is why the root is not a frame.
fn split_node(line: &str) -> Option<(usize, &str)> {
    let bytes = line.as_bytes();
    let mut index = 0;
    while let Some(b"| ") | Some(b"  ") = bytes.get(index..index + 2) {
        index += 2;
    }
    let body = line[index..]
        .strip_prefix("|-")
        .or_else(|| line[index..].strip_prefix("`-"))?;
    Some((index / 2, body))
}

/// The last `<path:line:col>` on a node line, when it names a file.
///
/// clang prints a location's path only when it differs from the last one it
/// printed, and it prints the declaration's *own* location after the source
/// range it came from. So a line like
/// `<line:1188:5, /…/qgis_sip.h:242:15> /…/qgsvectorlayer.h:1188:10 addFeature`
/// belongs to `qgsvectorlayer.h`: taking the first path would attribute every
/// `QGIS_DEPRECATED`-suffixed declaration to the annotation header, and would
/// poison the carried-forward state for the nodes below it.
fn location_file(text: &str) -> Option<&str> {
    let mut last = None;
    let mut rest = text;
    while let Some(open) = rest.find("</") {
        let after = &rest[open + 1..];
        let end = after.find(':')?;
        last = Some(&after[..end]);
        rest = &after[end..];
    }
    last.filter(|path| path.starts_with('/'))
}

/// A class (or struct/union) definition's name, when the node is one.
fn class_definition(text: &str) -> Option<&str> {
    if !text.starts_with("CXXRecordDecl") || !text.contains(" definition") {
        return None;
    }
    let at = text.find(" class ").or_else(|| text.find(" struct "))?;
    text[at + 1..]
        .split_whitespace()
        .nth(1)
        .filter(|name| *name != "definition")
}

/// The declaration kind a node records, or `None` when it records nothing.
///
/// Implicit declarations are excluded on purpose: the compiler's own copy
/// constructors, template instantiations and Qt's macro trampolines are not
/// declarations the headers state, and recording them would make an upgrade
/// diff unreadable and the inventory unstable across clang versions.
fn declared_kind(text: &str, nested_class: bool) -> Option<&'static str> {
    if text
        .split_whitespace()
        .any(|token| token.starts_with("implicit"))
    {
        return None;
    }
    if nested_class {
        return Some("class");
    }
    Some(match text.split_whitespace().next()? {
        "CXXMethodDecl" => "method",
        "CXXConstructorDecl" => "constructor",
        "CXXDestructorDecl" => "destructor",
        "CXXConversionDecl" => "conversion",
        "FieldDecl" => "field",
        "EnumDecl" => "enum",
        "VarDecl" => "variable",
        "TypedefDecl" | "TypeAliasDecl" => "typedef",
        "FunctionDecl" => "function",
        _ => return None,
    })
}

/// The member name and quoted type of a declaration node.
///
/// The dump spells a declaration as `<kind> <address> [prev <address>]
/// <location> [<bare location>] <name> '<type>' [<modifiers>]`. The location
/// comes first and is the only angle-bracketed group before the type, which is
/// why it is found from the left: an operator's own name can contain `<` and
/// `>` (`operator>`, `operator<<`), so searching for the last `>` would read
/// half the name as a location and invent a declaration called `=`.
fn split_name_and_type(text: &str) -> Option<(String, String)> {
    let start = text.find('\'')?;
    let end = text.rfind('\'')?;
    if end <= start {
        return None;
    }
    let head = &text[..start];
    let rest = match head.find('<') {
        Some(open) => head[open..]
            .find('>')
            .map_or(&head[open + 1..], |close| &head[open + close + 1..]),
        None => head,
    };
    let mut tokens: Vec<&str> = strip_location(rest.trim_start())
        .split_whitespace()
        .collect();
    while tokens.first().is_some_and(|token| is_modifier(token)) {
        tokens.remove(0);
    }
    while tokens.last().is_some_and(|token| *token == "definition") {
        tokens.pop();
    }
    if tokens.is_empty() {
        return None;
    }
    Some((tokens.join(" "), text[start + 1..end].to_string()))
}

/// Whether a leading token is a marker rather than part of a name.
fn is_modifier(token: &str) -> bool {
    token.starts_with("implicit")
        || matches!(
            token,
            "referenced"
                | "used"
                | "class"
                | "struct"
                | "union"
                | "enum"
                | "definition"
                | "constexpr"
                | "consteval"
                | "constinit"
                | "explicit"
                | "extern"
                | "inline"
                | "static"
                | "virtual"
                | "mutable"
                | "friend"
                | "thread_local"
        )
}

/// Drop leading locations (`col:16`, `line:72:5`, `/abs/file.h:72:5`) from
/// `text`, leaving the declaration's name.
///
/// A declaration whose source range spans a macro in another file prints its
/// own location *after* the range, path included:
/// `<line:1188:5, /…/qgis_sip.h:242:15> /…/qgsvectorlayer.h:1188:10 addFeature`.
/// Reading that path as part of the name would invent a declaration called
/// `/…/qgsvectorlayer.h:1188:10 addFeature` instead of `addFeature`.
fn strip_location(mut text: &str) -> &str {
    loop {
        let trimmed = text.trim_start();
        if trimmed.starts_with('/') {
            // A path-qualified location is one whitespace-delimited token.
            text = match trimmed.find(char::is_whitespace) {
                Some(end) => &trimmed[end..],
                None => return "",
            };
            continue;
        }
        let Some(rest) = ["line:", "col:"]
            .iter()
            .find_map(|prefix| trimmed.strip_prefix(prefix))
        else {
            return trimmed;
        };
        text = strip_numbers(rest);
    }
}

/// Drop `12` or `12:3` from the front of a bare location's remainder.
fn strip_numbers(mut rest: &str) -> &str {
    let digits = rest
        .find(|character: char| !character.is_ascii_digit())
        .unwrap_or(rest.len());
    rest = &rest[digits..];
    if let Some(after_colon) = rest.strip_prefix(':') {
        let digits = after_colon
            .find(|character: char| !character.is_ascii_digit())
            .unwrap_or(after_colon.len());
        rest = &after_colon[digits..];
    }
    rest
}

/// The parameter list of a function type, normalized to `Type,Type`.
///
/// `void (const QString &, bool)` becomes `constQString&,bool`; an empty or
/// `void` list becomes `""`, so `Qgis::version()` reads as a call. Commas
/// nested in template arguments or function-pointer types do not split.
#[must_use]
pub fn parameter_list(type_text: &str) -> String {
    let Some(open) = type_text.find('(') else {
        return String::new();
    };
    let mut depth = 0usize;
    let mut end = None;
    for (offset, character) in type_text[open..].char_indices() {
        match character {
            '(' => depth += 1,
            ')' => {
                depth -= 1;
                if depth == 0 {
                    end = Some(open + offset);
                    break;
                }
            }
            _ => {}
        }
    }
    let Some(end) = end else {
        return String::new();
    };
    let mut parameters: Vec<String> = Vec::new();
    let mut current = String::new();
    let mut brackets = 0i32;
    for character in type_text[open + 1..end].chars() {
        match character {
            '<' | '[' | '(' => brackets += 1,
            '>' | ']' | ')' => brackets -= 1,
            _ => {}
        }
        if character == ',' && brackets == 0 {
            parameters.push(std::mem::take(&mut current));
        } else {
            current.push(character);
        }
    }
    if !current.trim().is_empty() {
        parameters.push(current);
    }
    let parameters: Vec<String> = parameters
        .iter()
        .map(|parameter| parameter.chars().filter(|c| !c.is_whitespace()).collect())
        .filter(|parameter: &String| !parameter.is_empty())
        .collect();
    if parameters.len() == 1 && parameters[0] == "void" {
        return String::new();
    }
    parameters.join(",")
}

/// What a stack frame governs.
#[derive(Debug, Clone, Copy, Default)]
struct Frame {
    /// The scope in force below this node, empty at file scope.
    scope: Option<usize>,
    /// Whether this node *is* a class definition.
    class_here: bool,
    /// Whether this node is a namespace.
    namespace_here: bool,
    /// Access in force for declarations directly under a class definition.
    access: Option<Access>,
    /// Index into the discovered list when this node was recorded.
    record: Option<usize>,
}

/// The access specifier in force inside a class definition.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
enum Access {
    /// `public:` — the only access this extractor records.
    Public,
    /// `protected:` — modelled, never discovered.
    Protected,
    /// `private:` — the default for a `class`.
    #[default]
    Private,
}

/// Where a node sits, which decides both the kind list and the access rule.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Place {
    /// Directly under the translation unit.
    File,
    /// Directly under a namespace.
    Namespace,
    /// Directly under a class definition: a member.
    Class,
    /// Inside a function body, an expression, or anything else not recorded.
    Other,
}

/// Parse one `clang-check -ast-dump` dump into the declarations `headers` own.
///
/// Public for `tests/api_extract.rs`, which pins the model on dumps written by
/// hand: the tree by prefix, the file inherited across omitted locations,
/// access sections, overloads, nesting and deprecation.
///
/// # Examples
///
/// ```
/// use xtask::api_extract::parse_dump;
/// let dump = "|-CXXRecordDecl 0x1 </x/qgsvectorlayer.h:401:1, line:9:1> line:401:19 class QgsVectorLayer definition\n\
///             | |-AccessSpecDecl 0x2 <line:402:1> col:3 public\n\
///             | `-CXXMethodDecl 0x3 <line:403:5> col:10 name 'QString () const'\n";
/// let found = parse_dump(dump, &["qgsvectorlayer.h".to_string()]);
/// let ids: Vec<&str> = found.iter().map(|entry| entry.id.as_str()).collect();
/// // The class itself is a declaration of the header, and so is its method.
/// assert_eq!(ids, ["QgsVectorLayer", "QgsVectorLayer::name"]);
/// ```
#[must_use]
pub fn parse_dump(dump: &str, headers: &[String]) -> Vec<Discovery> {
    let targets: BTreeSet<&str> = headers.iter().map(String::as_str).collect();
    let mut scopes: Vec<String> = vec![String::new()];
    let mut last_file: Option<String> = None;
    let mut frames: Vec<Frame> = Vec::new();
    let mut discovered: Vec<Discovery> = Vec::new();
    let mut seen: BTreeSet<String> = BTreeSet::new();

    for line in dump.lines() {
        let Some((depth, text)) = split_node(line) else {
            continue;
        };
        if let Some(path) = location_file(text) {
            last_file = Some(path.to_string());
        }
        frames.truncate(depth);
        let parent = depth
            .checked_sub(1)
            .and_then(|index| frames.get(index).copied());
        let file_owns = last_file
            .as_deref()
            .and_then(|path| path.rsplit('/').next())
            .is_some_and(|name| targets.contains(name));

        let class_here = class_definition(text);
        let mut frame = Frame {
            scope: parent.and_then(|frame| frame.scope),
            class_here: class_here.is_some(),
            namespace_here: text.starts_with("NamespaceDecl"),
            access: None,
            record: None,
        };

        if class_here.is_some() {
            let name = class_here.unwrap_or_default();
            let scope = match parent.and_then(|frame| frame.scope) {
                Some(outer) if !scopes[outer].is_empty() => format!("{}::{name}", scopes[outer]),
                _ => name.to_string(),
            };
            scopes.push(scope);
            let access = if text.contains(" struct ") || text.contains(" union ") {
                Access::Public
            } else {
                Access::Private
            };
            frame.scope = Some(scopes.len() - 1);
            frame.access = Some(access);
        }

        if text.starts_with("AccessSpecDecl") {
            if let Some(scope) = frame.scope {
                for candidate in frames.iter_mut().rev() {
                    if candidate.scope == Some(scope) && candidate.class_here {
                        let trimmed = text.trim_end();
                        candidate.access = Some(if trimmed.ends_with("public") {
                            Access::Public
                        } else if trimmed.ends_with("protected") {
                            Access::Protected
                        } else {
                            Access::Private
                        });
                        break;
                    }
                }
            }
        }

        let place = match parent {
            None => Place::File,
            Some(frame) if frame.class_here => Place::Class,
            Some(frame) if frame.namespace_here => Place::Namespace,
            Some(_) => Place::Other,
        };
        let allowed = match place {
            Place::Class => true,
            Place::File | Place::Namespace => true,
            Place::Other => false,
        };
        let public = match place {
            Place::Class => parent
                .and_then(|frame| frame.access)
                .is_some_and(|access| access == Access::Public),
            Place::File | Place::Namespace => true,
            Place::Other => false,
        };

        if file_owns && allowed && public {
            if let Some(kind) = declared_kind(text, class_here.is_some()) {
                let parsed = match class_here {
                    Some(name) => Some((name.to_string(), String::new())),
                    None => split_name_and_type(text),
                };
                if let Some((member, type_text)) = parsed {
                    // A class definition opens its own scope, so its id *is*
                    // that scope and its `scope` is the one it sits in.
                    let scope = if class_here.is_some() {
                        parent
                            .and_then(|frame| frame.scope)
                            .map(|index| scopes[index].clone())
                            .unwrap_or_default()
                    } else {
                        frame
                            .scope
                            .map(|index| scopes[index].clone())
                            .unwrap_or_default()
                    };
                    // Only a function's parenthesised part identifies an
                    // overload; a field's type may contain one (a function
                    // pointer) and is not part of its identity.
                    let parameters = if matches!(
                        kind,
                        "method" | "constructor" | "destructor" | "conversion" | "function"
                    ) {
                        parameter_list(&type_text)
                    } else {
                        String::new()
                    };
                    let id = if class_here.is_some() {
                        match scope.as_str() {
                            "" => member.clone(),
                            scope => format!("{scope}::{member}"),
                        }
                    } else {
                        match (scope.as_str(), parameters.as_str()) {
                            ("", "") => member.clone(),
                            ("", parameters) => format!("{member}({parameters})"),
                            (scope, "") => format!("{scope}::{member}"),
                            (scope, parameters) => format!("{scope}::{member}({parameters})"),
                        }
                    };
                    if seen.insert(id.clone()) {
                        let deprecated = text.contains("DeprecatedAttr");
                        frame.record = Some(discovered.len());
                        discovered.push(Discovery {
                            id,
                            kind: kind.to_string(),
                            header: last_file
                                .as_deref()
                                .and_then(|path| path.rsplit('/').next())
                                .unwrap_or_default()
                                .to_string(),
                            scope,
                            member,
                            deprecated,
                        });
                    }
                }
            }
        }

        // A deprecation attribute is a child of the declaration it marks.
        if text.contains("DeprecatedAttr") {
            if let Some(record) = parent.and_then(|frame| frame.record) {
                discovered[record].deprecated = true;
            }
        }

        frames.push(frame);
    }

    discovered.sort();
    discovered
}

/// Give every discovered declaration its manifest status, reason and range.
///
/// The precedence is the module table: the headers' own deprecation wins, then
/// the manifest's review, then `unsupported` with [`REASON_NOT_REVIEWED`].
#[must_use]
pub fn classify(
    discovered: &[Discovery],
    manifest: &ApiManifest,
    clang_version: &str,
) -> Inventory {
    let reviewed: BTreeMap<&str, &crate::api_manifest::Declaration> = manifest
        .declarations
        .iter()
        .map(|declaration| (scoped_name(&declaration.id), declaration))
        .collect();
    let floor = format!(">={},<4", manifest.qgis.min_version);
    let mut counts: BTreeMap<String, usize> = BTreeMap::new();
    let declarations: Vec<InventoryEntry> = discovered
        .iter()
        .map(|discovery| {
            let name = scoped_name(&discovery.id);
            let review = reviewed.get(name).copied();
            let (status, since, version_range, reason) = match (discovery.deprecated, review) {
                (true, review) => (
                    "deprecated".to_string(),
                    review.map_or_else(|| "unknown".to_string(), |d| d.since.clone()),
                    review.map_or_else(|| floor.clone(), |d| d.version_range.clone()),
                    REASON_DEPRECATED.to_string(),
                ),
                (false, Some(declaration)) => (
                    declaration.status.clone(),
                    declaration.since.clone(),
                    declaration.version_range.clone(),
                    declaration.reason.clone(),
                ),
                (false, None) => (
                    "unsupported".to_string(),
                    "unknown".to_string(),
                    floor.clone(),
                    REASON_NOT_REVIEWED.to_string(),
                ),
            };
            *counts.entry(status.clone()).or_default() += 1;
            InventoryEntry {
                id: discovery.id.clone(),
                kind: discovery.kind.clone(),
                header: discovery.header.clone(),
                status,
                since,
                version_range,
                reason,
            }
        })
        .collect();

    Inventory {
        extractor: EXTRACTOR_ID.to_string(),
        clang_version: clang_version.to_string(),
        qgis_min_version: manifest.qgis.min_version.clone(),
        qgis_tested_version: manifest.qgis.tested_version.clone(),
        headers: manifest.source.headers.clone(),
        counts,
        declarations,
    }
}

/// The `Scope::name` part of an id, without the parenthesised type list.
///
/// Both spellings of a scope-insensitive id (`Class::name`, `Class::name(...)`)
/// and the manifest's synthetic `...-new` suffix reduce to the same key, which
/// is what the reviewed-to-discovered check matches on.
#[must_use]
pub fn scoped_name(id: &str) -> &str {
    let name = id.split('(').next().unwrap_or(id);
    name.strip_suffix("-new").unwrap_or(name)
}

/// Render the inventory as the checked-in JSON: one declaration per line, so
/// a QGIS upgrade's diff is a list of declarations rather than a reformat.
#[must_use]
pub fn render_inventory(inventory: &Inventory) -> String {
    let mut out = String::from("{\n");
    out.push_str(&format!(
        "  \"extractor\": {},\n",
        json_string(&inventory.extractor)
    ));
    out.push_str(&format!(
        "  \"clang_version\": {},\n",
        json_string(&inventory.clang_version)
    ));
    out.push_str(&format!(
        "  \"qgis_min_version\": {},\n",
        json_string(&inventory.qgis_min_version)
    ));
    out.push_str(&format!(
        "  \"qgis_tested_version\": {},\n",
        json_string(&inventory.qgis_tested_version)
    ));
    out.push_str("  \"headers\": [\n");
    for (index, header) in inventory.headers.iter().enumerate() {
        let comma = if index + 1 == inventory.headers.len() {
            ""
        } else {
            ","
        };
        out.push_str(&format!("    {}{comma}\n", json_string(header)));
    }
    out.push_str("  ],\n  \"counts\": {\n");
    let total = inventory.counts.len();
    for (index, (status, count)) in inventory.counts.iter().enumerate() {
        let comma = if index + 1 == total { "" } else { "," };
        out.push_str(&format!("    {}: {count}{comma}\n", json_string(status)));
    }
    out.push_str("  },\n  \"declarations\": [\n");
    for (index, entry) in inventory.declarations.iter().enumerate() {
        let comma = if index + 1 == inventory.declarations.len() {
            ""
        } else {
            ","
        };
        let encoded = serde_json::to_string(entry).expect("an entry serializes");
        out.push_str(&format!("    {encoded}{comma}\n"));
    }
    out.push_str("  ]\n}\n");
    out
}

/// A JSON string literal for a value this module controls.
fn json_string(value: &str) -> String {
    serde_json::to_string(value).expect("a string serializes")
}

/// The one-line summary the lint prints, in the style of the other lints.
#[must_use]
pub fn inventory_summary(inventory: &Inventory) -> String {
    let reviewed: usize = inventory
        .counts
        .iter()
        .filter(|(status, _)| status.as_str() != "unsupported")
        .map(|(_, count)| count)
        .sum();
    format!(
        "api-inventory: {} declarations in {} header(s) — {} reviewed, {} unsupported",
        inventory.declarations.len(),
        inventory.headers.len(),
        reviewed,
        inventory
            .counts
            .get("unsupported")
            .copied()
            .unwrap_or_default()
    )
}

/// The command line the extractor hands clang, as a pure seam for tests.
///
/// `probe` is the generated translation unit, and the include contract is
/// `clang-tidy`'s: Qt and QGIS includes in front, then the conda GCC headers,
/// the sysroot and `-nostdinc++` so clang parses the same C++ library the
/// build does. Without the last three, clang falls back to the host's
/// libstdc++ and the dump stops being a complete parse of the headers.
#[must_use]
pub fn extraction_arguments(prefix: &Path, gcc_include: &Path, probe: &Path) -> Vec<String> {
    let include = |path: &str| format!("-I{}/{}", prefix.display(), path);
    let mut arguments = vec![
        "-std=c++17".to_string(),
        include("include/qt"),
        include("include/qt/QtCore"),
        include("include/qt/QtGui"),
        include("include/qt/QtWidgets"),
        include("include/qt/QtXml"),
        include("include/qgis"),
        format!(
            "--sysroot={}",
            prefix.join("x86_64-conda-linux-gnu/sysroot").display()
        ),
        format!("-I{}", gcc_include.display()),
        "-nostdinc++".to_string(),
    ];
    for directory in ["c++", "c++/x86_64-conda-linux-gnu", "c++/backward"] {
        arguments.push(format!("-isystem {}/{}", gcc_include.display(), directory));
    }
    arguments.push(probe.display().to_string());
    arguments
}

/// Run the extractor and return the dump, the clang version and the headers.
///
/// Fails loudly when `CONDA_PREFIX` is unset, when a declared header is not
/// installed, or when clang reports an error: a short inventory that still
/// looked green would defeat the whole check.
pub fn extract(root: &Path) -> Result<(String, String, Vec<String>)> {
    let prefix = std::env::var("CONDA_PREFIX")
        .context("CONDA_PREFIX is not set — run this under `pixi run -e default`")?;
    let manifest = validate_manifest(
        &fs::read_to_string(root.join(MANIFEST_PATH))
            .with_context(|| format!("read {MANIFEST_PATH}"))?,
    )?;
    let headers = &manifest.source.headers;
    if headers.is_empty() {
        bail!("the API manifest declares no source.headers to extract");
    }
    for header in headers {
        let path = Path::new(&prefix).join("include/qgis").join(header);
        if !path.is_file() {
            bail!(
                "declared header {header} is not installed at {} — is the QGIS prefix current?",
                path.display()
            );
        }
    }

    let gcc_include = first_matching_file(&Path::new(&prefix).join("lib/gcc"), |path| {
        path.file_name() == Some(std::ffi::OsStr::new("stddef.h"))
    })
    .and_then(|path| path.parent().map(Path::to_path_buf))
    .context("api-extract: no stddef.h under $CONDA_PREFIX/lib/gcc")?;

    let work = std::env::temp_dir().join(format!("qgis-rs-api-extract-{}", std::process::id()));
    fs::create_dir_all(&work).with_context(|| format!("create {}", work.display()))?;
    let probe = work.join("probe.cpp");
    let probe_source = headers
        .iter()
        .map(|header| format!("#include <{header}>\n"))
        .collect::<String>()
        + "int qgis_rs_probe_tu;\n";
    fs::write(&probe, probe_source).with_context(|| format!("write {}", probe.display()))?;

    let arguments = extraction_arguments(Path::new(&prefix), &gcc_include, &probe);
    let database = serde_json::json!([{
        "directory": root.display().to_string(),
        "file": probe.display().to_string(),
        "command": format!("c++ {}", arguments.join(" ")),
    }]);
    fs::write(
        work.join("compile_commands.json"),
        serde_json::to_string(&database)?,
    )
    .context("write the extractor's private compile database")?;

    let clang_version = clang_version()?;
    let output = Command::new("clang-check")
        .arg("-p")
        .arg(&work)
        .arg("-ast-dump")
        .arg(&probe)
        .output()
        .context("run clang-check (is the `default` environment active?)")?;
    let _ = fs::remove_dir_all(&work);
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let first = stderr
            .lines()
            .find(|line| line.contains("error:"))
            .unwrap_or_else(|| stderr.lines().next().unwrap_or("no diagnostics"));
        bail!(
            "clang-check failed to parse the declared headers ({}) — {first}",
            output.status
        );
    }
    let dump = String::from_utf8(output.stdout).context("clang-check wrote non-UTF-8 output")?;
    Ok((dump, clang_version, headers.clone()))
}

/// The clang version, read from the same binary the extraction runs.
fn clang_version() -> Result<String> {
    let output = Command::new("clang-check")
        .arg("--version")
        .output()
        .context("run clang-check --version")?;
    let text = String::from_utf8_lossy(&output.stdout);
    Ok(text
        .lines()
        .find_map(|line| line.trim().strip_prefix("LLVM version "))
        .map(|version| {
            version
                .split_whitespace()
                .next()
                .unwrap_or(version)
                .to_string()
        })
        .unwrap_or_else(|| "unknown".to_string()))
}

/// Extract, classify and check the checkout against the checked-in inventory.
///
/// This is what the `check-api-inventory` lint runs, so `pixi run gates` fails
/// on a stale inventory, on a reviewed declaration the headers no longer
/// declare, and on an entry missing its status, reason or version range.
pub fn verify_repository(root: &Path) -> Result<()> {
    let (dump, clang_version, headers) = extract(root)?;
    let inventory = verify_with(root, &dump, &clang_version, &headers)?;
    println!("{}", inventory_summary(&inventory));
    Ok(())
}

/// The verification seam: everything [`verify_repository`] checks, against a
/// dump the caller supplies.
///
/// Public for `tests/api_extract.rs`, which writes a scratch manifest, a
/// scratch inventory and a synthetic dump, then damages each of them and
/// requires this function to name the drift.
pub fn verify_with(
    root: &Path,
    dump: &str,
    clang_version: &str,
    headers: &[String],
) -> Result<Inventory> {
    let manifest = validate_manifest(
        &fs::read_to_string(root.join(MANIFEST_PATH))
            .with_context(|| format!("read {}", root.join(MANIFEST_PATH).display()))?,
    )?;
    let discovered = parse_dump(dump, headers);
    let inventory = classify(&discovered, &manifest, clang_version);

    for entry in &inventory.declarations {
        if entry.id.is_empty() {
            bail!("api-inventory: an entry has an empty id");
        }
        if entry.status.is_empty() {
            bail!("api-inventory: {} has no status", entry.id);
        }
        if entry.reason.trim().is_empty() {
            bail!("api-inventory: {} has no reason", entry.id);
        }
        if entry.version_range.trim().is_empty() {
            bail!("api-inventory: {} has no version range", entry.id);
        }
    }

    let path = root.join(INVENTORY_PATH);
    let expected = render_inventory(&inventory);
    let actual = fs::read_to_string(&path)
        .with_context(|| format!("read {}; run `pixi run xtask api-extract`", path.display()))?;
    if actual != expected {
        bail!(
            "api-inventory: {} is stale; run `pixi run xtask api-extract` and review the diff",
            path.display()
        );
    }

    let discovered_names: BTreeSet<&str> = inventory
        .declarations
        .iter()
        .map(|entry| scoped_name(&entry.id))
        .collect();
    for declaration in &manifest.declarations {
        // Manager-owned ids (`native-manager::api_describe`) name operations,
        // not header declarations, so the extractor cannot discover them.
        if declaration.kind == "operation" {
            continue;
        }
        let name = scoped_name(&declaration.id);
        if !discovered_names.contains(name) {
            bail!(
                "api-inventory: {} is reviewed but the declared headers no longer declare it",
                declaration.id
            );
        }
    }
    Ok(inventory)
}

/// `api-extract` itself: write the inventory, or check the checked-in one.
pub fn run(check: bool) -> Result<()> {
    let root = repo_root();
    if check {
        return verify_repository(&root);
    }
    let (dump, clang_version, headers) = extract(&root)?;
    let manifest = validate_manifest(
        &fs::read_to_string(root.join(MANIFEST_PATH))
            .with_context(|| format!("read {MANIFEST_PATH}"))?,
    )?;
    let inventory = classify(&parse_dump(&dump, &headers), &manifest, &clang_version);
    let path = root.join(INVENTORY_PATH);
    fs::write(&path, render_inventory(&inventory))
        .with_context(|| format!("write {}", path.display()))?;
    println!("{}", inventory_summary(&inventory));
    println!("wrote {}", path.display());
    Ok(())
}
