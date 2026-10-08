//! The API extractor's public seam: an AST dump in, an inventory out.
//!
//! The dump here is written by hand rather than captured, so each test states
//! the clang spelling it is pinning. Every one of these spellings came out of a
//! real `clang-check -ast-dump` of the installed QGIS headers, including the
//! ones that first looked like parser trivia and were bugs:
//!
//! * a declaration whose source range crosses a `QGIS_DEPRECATED` macro prints
//!   a second, path-qualified location *after* the range, and reading it as
//!   part of the name invents a declaration called
//!   `/…/qgsvectorlayer.h:1188:10 addFeature`;
//! * `operator<<` and `operator>=` carry angle brackets of their own, so
//!   "the name follows the last `>`" reads half the name as a location;
//! * a class member's location omits its file whenever the previous line
//!   printed it, so the file has to be carried forward;
//! * a `Q_OBJECT` trampoline lives inside a target class's subtree with a Qt
//!   header's location, so the file filter is what keeps it out.

use std::fs;
use std::path::{Path, PathBuf};

use xtask::api_extract::{
    classify, extraction_arguments, parse_dump, render_inventory, scoped_name, verify_with,
    Discovery, EXTRACTOR_ID, INVENTORY_PATH, REASON_DEPRECATED, REASON_NOT_REVIEWED,
};
use xtask::api_manifest::MANIFEST_PATH;

/// A minimal, valid manifest: one reviewed declaration, one operation, and the
/// seven required mapping categories.
fn manifest_json(headers: &[&str], declarations: &str) -> String {
    let mappings: Vec<String> = [
        "ownership",
        "invalidation",
        "overload",
        "enum",
        "variant",
        "binary_artifact",
        "paging",
    ]
    .iter()
    .map(|category| {
        format!(r#"{{"category":"{category}","qgis_type":"t","wire_type":"w","rule":"r"}}"#)
    })
    .collect();
    let headers: Vec<String> = headers.iter().map(|h| format!(r#""{h}""#)).collect();
    format!(
        r#"{{
  "manifest_version": 1,
  "qgis": {{"min_version": "3.44.9", "tested_version": "3.44.14"}},
  "source": {{"extractor": "test", "headers": [{}], "metadata": []}},
  "declarations": [{}],
  "mappings": [{}],
  "operations": [{{
    "name": "layer_fields",
    "handler": "layer_fields",
    "codec": "json_object",
    "request_codec": "layer_fields_request",
    "result_codec": "layer_fields_result",
    "requires_initialization": true
  }}],
  "exclusions": []
}}"#,
        headers.join(", "),
        declarations,
        mappings.join(", ")
    )
}

fn reviewed_fields() -> String {
    r#"{
      "id": "QgsVectorLayer::fields",
      "kind": "method",
      "module": "core-data",
      "status": "supported_manual",
      "since": "3.0",
      "version_range": ">=3.0,<4",
      "reason": "Reviewed: fields are copied as a schema snapshot.",
      "ownership": "borrowed_snapshot",
      "operation": "layer_fields",
      "handler": "layer_fields"
    }"#
    .to_string()
}

fn parse(lines: &[&str], headers: &[&str]) -> Vec<Discovery> {
    let headers: Vec<String> = headers.iter().map(|header| (*header).to_string()).collect();
    parse_dump(&lines.join("\n"), &headers)
}

fn ids(found: &[Discovery]) -> Vec<&str> {
    found.iter().map(|entry| entry.id.as_str()).collect()
}

const CLASS: &str = "|-CXXRecordDecl 0x1 </q/qgsvectorlayer.h:401:1, line:999:1> line:401:19 class QgsVectorLayer definition";

// ---------------------------------------------------------------- the parser

#[test]
fn a_declared_header_contributes_its_public_members() {
    let found = parse(
        &[
            CLASS,
            "| |-AccessSpecDecl 0x2 <line:402:3> col:3 public",
            "| |-CXXConstructorDecl 0x3 <line:403:5, col:44> col:5 QgsVectorLayer 'void (const QString &, const QString &)'",
            "| |-CXXDestructorDecl 0x4 <line:404:5> col:5 ~QgsVectorLayer 'void () noexcept'",
            "| |-CXXMethodDecl 0x5 <line:405:5> col:10 fields 'QgsFields () const'",
            "| |-FieldDecl 0x6 <line:406:5> col:12 mFields 'QgsFields'",
            "| |-EnumDecl 0x7 <line:407:5> col:10 Capabilities 'unsigned int'",
            "| |-VarDecl 0x8 <line:408:5> col:40 mSettings 'const QgsSettingsEntryBool *' static",
            "| `-CXXMethodDecl 0x9 <line:409:5> col:10 addFeature 'bool (QgsFeature &, QgsFeatureSink::Flags)'",
        ],
        &["qgsvectorlayer.h"],
    );

    assert_eq!(
        ids(&found),
        [
            "QgsVectorLayer",
            "QgsVectorLayer::Capabilities",
            "QgsVectorLayer::QgsVectorLayer(constQString&,constQString&)",
            "QgsVectorLayer::addFeature(QgsFeature&,QgsFeatureSink::Flags)",
            "QgsVectorLayer::fields",
            "QgsVectorLayer::mFields",
            "QgsVectorLayer::mSettings",
            "QgsVectorLayer::~QgsVectorLayer",
        ]
    );
    let fields = found
        .iter()
        .find(|entry| entry.id == "QgsVectorLayer::fields")
        .expect("the method is discovered");
    assert_eq!(fields.kind, "method");
    assert_eq!(fields.header, "qgsvectorlayer.h");
    assert_eq!(fields.scope, "QgsVectorLayer");
    assert_eq!(fields.member, "fields");
}

#[test]
fn a_private_or_protected_section_stops_discovery() {
    let found = parse(
        &[
            CLASS,
            "| |-AccessSpecDecl 0x2 <line:402:3> col:3 public",
            "| |-CXXMethodDecl 0x3 <line:403:5> col:10 name 'QString () const'",
            "| |-AccessSpecDecl 0x4 <line:404:3> col:3 private",
            "| |-CXXMethodDecl 0x5 <line:405:5> col:10 secret 'void ()'",
            "| |-AccessSpecDecl 0x6 <line:406:3> col:3 protected",
            "| `-CXXMethodDecl 0x7 <line:407:5> col:10 guarded 'void ()'",
        ],
        &["qgsvectorlayer.h"],
    );

    assert_eq!(ids(&found), ["QgsVectorLayer", "QgsVectorLayer::name"]);
}

#[test]
fn a_class_definition_opens_a_scope_for_its_nested_members() {
    let found = parse(
        &[
            CLASS,
            "| |-AccessSpecDecl 0x2 <line:402:3> col:3 public",
            "| |-CXXRecordDecl 0x3 <line:420:5, line:440:5> line:420:12 struct LayerOptions definition",
            "| | |-AccessSpecDecl 0x4 <line:421:7> col:7 public",
            "| | `-FieldDecl 0x5 <line:422:7> col:12 loadDefaultStyle 'bool'",
            "| `-CXXMethodDecl 0x6 <line:460:5> col:10 options 'const QgsVectorLayer::LayerOptions &() const'",
        ],
        &["qgsvectorlayer.h"],
    );

    assert_eq!(
        ids(&found),
        [
            "QgsVectorLayer",
            "QgsVectorLayer::LayerOptions",
            "QgsVectorLayer::LayerOptions::loadDefaultStyle",
            "QgsVectorLayer::options",
        ]
    );
    let nested = found
        .iter()
        .find(|entry| entry.id == "QgsVectorLayer::LayerOptions")
        .expect("the nested class is discovered");
    assert_eq!(nested.kind, "class");
    assert_eq!(nested.scope, "QgsVectorLayer");
}

#[test]
fn an_abbreviated_location_inherits_the_last_printed_file() {
    // clang prints the path only when it changes; the second member's location
    // is `<col:7>` and belongs to qgsvectorlayer.h, not to the Qt header the
    // trampoline above it named.
    let found = parse(
        &[
            CLASS,
            "| |-CXXMethodDecl 0x2 </q/qt/QtCore/qobjectdefs.h:191:5> col:5 qt_check_for_QGADGET_macro 'void ()'",
            "| |-AccessSpecDecl 0x3 </q/qgsvectorlayer.h:402:3> col:3 public",
            "| |-CXXMethodDecl 0x4 <col:7> col:10 name 'QString () const'",
            "| `-CXXMethodDecl 0x5 <col:7> col:10 crs 'QgsCoordinateReferenceSystem () const'",
        ],
        &["qgsvectorlayer.h"],
    );

    assert_eq!(
        ids(&found),
        [
            "QgsVectorLayer",
            "QgsVectorLayer::crs",
            "QgsVectorLayer::name"
        ]
    );
    assert!(found.iter().all(|entry| entry.header == "qgsvectorlayer.h"));
}

#[test]
fn a_declaration_from_another_header_is_not_discovered() {
    let found = parse(
        &[
            CLASS,
            "| |-CXXMethodDecl 0x2 </q/qt/QtCore/qobjectdefs.h:199:108> col:47 qt_static_metacall 'void (QObject *, QMetaObject::Call, int, void **)' static",
            "| `-CXXMethodDecl 0x3 </q/qt/QtCore/qobjectdefs.h:200:5> col:10 metaObject 'const QMetaObject *() const' virtual",
        ],
        &["qgsvectorlayer.h"],
    );

    // The class definition itself is in the declared header and is recorded;
    // nothing the Qt trampolines declare is.
    assert_eq!(ids(&found), ["QgsVectorLayer"]);
    assert!(found.iter().all(|entry| entry.header == "qgsvectorlayer.h"));
}

#[test]
fn a_macro_expansion_does_not_rename_the_declaration() {
    // The real spelling: the range begins on line 1188 but expands through
    // QGIS_DEPRECATED in qgis_sip.h, and the declaration's own location comes
    // last, path included.
    let found = parse(
        &[
            CLASS,
            "| |-AccessSpecDecl 0x2 <line:1188:3> col:3 public",
            "| `-CXXMethodDecl 0x3 <line:1188:5, /q/qgis_sip.h:242:15> /q/qgsvectorlayer.h:1188:10 addFeature 'bool (QgsFeature &, QgsFeatureSink::Flags)'",
        ],
        &["qgsvectorlayer.h"],
    );

    assert_eq!(
        ids(&found),
        [
            "QgsVectorLayer",
            "QgsVectorLayer::addFeature(QgsFeature&,QgsFeatureSink::Flags)",
        ]
    );
    let method = found
        .iter()
        .find(|entry| entry.member == "addFeature")
        .expect("the method is discovered");
    assert_eq!(method.header, "qgsvectorlayer.h");
}

#[test]
fn an_operator_keeps_its_own_angle_brackets() {
    let found = parse(
        &[
            "|-FunctionDecl 0x1 </q/qgscoordinatereferencesystem.h:1332:1, line:1375:1> line:1332:22 operator<< 'std::ostream &(std::ostream &, const QgsCoordinateReferenceSystem &)'",
            "|-FunctionDecl 0x2 </q/qgscoordinatereferencesystem.h:1378:1> col:18 operator>= 'bool (const QgsCoordinateReferenceSystem &, const QgsCoordinateReferenceSystem &)'",
        ],
        &["qgscoordinatereferencesystem.h"],
    );

    assert_eq!(
        ids(&found),
        [
            "operator<<(std::ostream&,constQgsCoordinateReferenceSystem&)",
            "operator>=(constQgsCoordinateReferenceSystem&,constQgsCoordinateReferenceSystem&)",
        ]
    );
}

#[test]
fn implicit_members_are_not_recorded() {
    let found = parse(
        &[
            CLASS,
            "| |-AccessSpecDecl 0x1 <line:409:3> col:3 public",
            "| |-CXXMethodDecl 0x2 <line:410:5> col:19 implicit operator= 'QgsVectorLayer &(const QgsVectorLayer &)' inline",
            "| |-CXXConstructorDecl 0x3 <line:411:5> col:5 implicit-inline QgsVectorLayer 'void (const QgsVectorLayer &)'",
            "| `-CXXMethodDecl 0x4 <line:412:5> col:10 name 'QString () const'",
        ],
        &["qgsvectorlayer.h"],
    );

    assert_eq!(ids(&found), ["QgsVectorLayer", "QgsVectorLayer::name"]);
}

#[test]
fn overloads_are_distinguished_by_parameter_type() {
    let found = parse(
        &[
            CLASS,
            "| |-AccessSpecDecl 0x2 <line:402:3> col:3 public",
            "| |-CXXMethodDecl 0x3 <line:403:5> col:10 getFeatures 'QgsFeatureIterator (const QString &) const'",
            "| |-CXXMethodDecl 0x4 <line:404:5> col:10 getFeatures 'QgsFeatureIterator (const QgsFeatureIds &) const'",
            "| `-CXXMethodDecl 0x5 <line:405:5> col:10 getFeatures 'QgsFeatureIterator () const'",
        ],
        &["qgsvectorlayer.h"],
    );

    assert_eq!(
        ids(&found),
        [
            "QgsVectorLayer",
            "QgsVectorLayer::getFeatures",
            "QgsVectorLayer::getFeatures(constQString&)",
            "QgsVectorLayer::getFeatures(constQgsFeatureIds&)",
        ]
    );
}

#[test]
fn deprecation_comes_from_the_attribute_child() {
    let found = parse(
        &[
            CLASS,
            "| |-AccessSpecDecl 0x2 <line:402:3> col:3 public",
            "| |-CXXMethodDecl 0x3 <line:403:5> col:10 oldName 'QString () const'",
            "| | `-DeprecatedAttr 0x4 </q/qgis_core.h:15:42> \"\" \"\"",
            "| `-CXXMethodDecl 0x5 <line:404:5> col:10 name 'QString () const'",
        ],
        &["qgsvectorlayer.h"],
    );

    let old = found
        .iter()
        .find(|entry| entry.member == "oldName")
        .expect("the deprecated method is discovered");
    assert!(old.deprecated);
    assert!(!found
        .iter()
        .any(|entry| entry.member == "name" && entry.deprecated));
}

#[test]
fn the_same_declaration_is_discovered_once() {
    let found = parse(
        &[
            CLASS,
            "| |-AccessSpecDecl 0x2 <line:402:3> col:3 public",
            "| |-CXXMethodDecl 0x3 <line:403:5> col:10 name 'QString () const'",
            "| `-CXXMethodDecl 0x4 <line:404:5> col:10 name 'QString () const'",
        ],
        &["qgsvectorlayer.h"],
    );

    assert_eq!(ids(&found), ["QgsVectorLayer", "QgsVectorLayer::name"]);
}

// ------------------------------------------------------------- the inventory

fn reviewed_and_unreviewed() -> (Vec<Discovery>, String) {
    let dump = [
        CLASS,
        "| |-AccessSpecDecl 0x2 <line:402:3> col:3 public",
        "| |-CXXMethodDecl 0x3 <line:403:5> col:10 fields 'QgsFields () const'",
        "| |-CXXMethodDecl 0x4 <line:404:5> col:10 subsetString 'QString () const'",
        "| `-CXXMethodDecl 0x5 <line:405:5> col:10 oldThing 'void ()'",
    ]
    .join("\n");
    let headers = vec!["qgsvectorlayer.h".to_string()];
    (parse_dump(&dump, &headers), dump)
}

#[test]
fn a_reviewed_declaration_carries_the_manifest_decision() {
    let (discovered, _) = reviewed_and_unreviewed();
    let manifest = xtask::api_manifest::validate_manifest(&manifest_json(
        &["qgsvectorlayer.h"],
        &reviewed_fields(),
    ))
    .expect("fixture manifest is valid");
    let inventory = classify(&discovered, &manifest, "22.1.8");

    let entry = inventory
        .declarations
        .iter()
        .find(|entry| entry.id == "QgsVectorLayer::fields")
        .expect("the reviewed declaration is in the inventory");
    assert_eq!(entry.status, "supported_manual");
    assert_eq!(entry.since, "3.0");
    assert_eq!(entry.version_range, ">=3.0,<4");
    assert_eq!(
        entry.reason,
        "Reviewed: fields are copied as a schema snapshot."
    );
}

#[test]
fn an_unreviewed_declaration_is_unsupported_with_the_pinned_floor() {
    let (discovered, _) = reviewed_and_unreviewed();
    let manifest = xtask::api_manifest::validate_manifest(&manifest_json(
        &["qgsvectorlayer.h"],
        &reviewed_fields(),
    ))
    .expect("fixture manifest is valid");
    let inventory = classify(&discovered, &manifest, "22.1.8");

    let entry = inventory
        .declarations
        .iter()
        .find(|entry| entry.id == "QgsVectorLayer::subsetString")
        .expect("the unreviewed declaration is still recorded");
    assert_eq!(entry.status, "unsupported");
    assert_eq!(entry.since, "unknown");
    assert_eq!(entry.version_range, ">=3.44.9,<4");
    assert_eq!(entry.reason, REASON_NOT_REVIEWED);
    assert_eq!(inventory.counts.get("supported_manual"), Some(&1));
    assert_eq!(inventory.counts.get("unsupported"), Some(&3));
}

#[test]
fn deprecation_outranks_a_review() {
    let (mut discovered, _) = reviewed_and_unreviewed();
    for entry in &mut discovered {
        if entry.id == "QgsVectorLayer::fields" {
            entry.deprecated = true;
        }
    }
    let manifest = xtask::api_manifest::validate_manifest(&manifest_json(
        &["qgsvectorlayer.h"],
        &reviewed_fields(),
    ))
    .expect("fixture manifest is valid");
    let inventory = classify(&discovered, &manifest, "22.1.8");

    let entry = inventory
        .declarations
        .iter()
        .find(|entry| entry.id == "QgsVectorLayer::fields")
        .expect("the reviewed declaration is in the inventory");
    assert_eq!(entry.status, "deprecated");
    assert_eq!(entry.reason, REASON_DEPRECATED);
}

#[test]
fn the_inventory_renders_one_declaration_per_line_in_id_order() {
    let (discovered, _) = reviewed_and_unreviewed();
    let manifest = xtask::api_manifest::validate_manifest(&manifest_json(
        &["qgsvectorlayer.h"],
        &reviewed_fields(),
    ))
    .expect("fixture manifest is valid");
    let inventory = classify(&discovered, &manifest, "22.1.8");
    let rendered = render_inventory(&inventory);

    assert!(rendered.contains(r#""extractor": "clang-ast-text/public-members/v1""#));
    assert!(rendered.contains(r#""clang_version": "22.1.8""#));
    let lines: Vec<&str> = rendered
        .lines()
        .filter(|line| line.trim_start().starts_with("{\"id\""))
        .collect();
    assert_eq!(lines.len(), inventory.declarations.len());
    assert!(lines[0].contains("\"id\":\"QgsVectorLayer\","));
    assert!(lines[1].contains("QgsVectorLayer::fields"));
    assert!(lines[2].contains("QgsVectorLayer::oldThing"));
    assert!(lines[3].contains("QgsVectorLayer::subsetString"));
    // The volatile extractor identity is the module's own constant, so a
    // policy change shows up as an inventory diff rather than silently.
    assert!(rendered.contains(EXTRACTOR_ID));
}

#[test]
fn the_extraction_contract_is_clang_tidys() {
    let prefix = Path::new("/prefix");
    let gcc = Path::new("/prefix/lib/gcc/x86_64-conda-linux-gnu/14.4.0/include");
    let probe = Path::new("/tmp/qgis-rs-api-extract-1/probe.cpp");
    let arguments = extraction_arguments(prefix, gcc, probe);

    for expected in [
        "-I/prefix/include/qgis",
        "-I/prefix/include/qt/QtCore",
        "--sysroot=/prefix/x86_64-conda-linux-gnu/sysroot",
        "-I/prefix/lib/gcc/x86_64-conda-linux-gnu/14.4.0/include",
        "-nostdinc++",
        "-isystem /prefix/lib/gcc/x86_64-conda-linux-gnu/14.4.0/include/c++",
        "-isystem /prefix/lib/gcc/x86_64-conda-linux-gnu/14.4.0/include/c++/backward",
    ] {
        assert!(
            arguments.contains(&expected.to_string()),
            "missing {expected}"
        );
    }
    assert_eq!(
        arguments.last().map(String::as_str),
        Some("/tmp/qgis-rs-api-extract-1/probe.cpp")
    );
}

// --------------------------------------------------------------- the checkout

/// A scratch repository root holding the two files `verify_with` reads.
fn scratch_repository(name: &str, headers: &[&str], declarations: &str) -> PathBuf {
    let root =
        std::env::temp_dir().join(format!("xtask-api-extract-{name}-{}", std::process::id()));
    let _ = fs::remove_dir_all(&root);
    let manifest = root.join(MANIFEST_PATH);
    fs::create_dir_all(manifest.parent().expect("manifest path has a parent"))
        .expect("create scratch manifest directory");
    fs::write(&manifest, manifest_json(headers, declarations)).expect("write scratch manifest");
    let inventory = root.join(INVENTORY_PATH);
    fs::create_dir_all(inventory.parent().expect("inventory path has a parent"))
        .expect("create scratch inventory directory");
    root
}

fn scratch_headers(headers: &[&str]) -> Vec<String> {
    headers.iter().map(|header| (*header).to_string()).collect()
}

#[test]
fn a_current_inventory_passes_verification() {
    let headers = ["qgsvectorlayer.h"];
    let root = scratch_repository("current", &headers, &reviewed_fields());
    let (_, dump) = reviewed_and_unreviewed();
    let manifest =
        xtask::api_manifest::validate_manifest(&manifest_json(&headers, &reviewed_fields()))
            .expect("fixture manifest is valid");
    let inventory = classify(
        &parse_dump(&dump, &scratch_headers(&headers)),
        &manifest,
        "22.1.8",
    );
    fs::write(root.join(INVENTORY_PATH), render_inventory(&inventory)).expect("write inventory");

    verify_with(&root, &dump, "22.1.8", &scratch_headers(&headers))
        .expect("a freshly written inventory verifies");
}

#[test]
fn a_stale_inventory_is_named_with_its_regeneration_command() {
    let headers = ["qgsvectorlayer.h"];
    let root = scratch_repository("stale", &headers, &reviewed_fields());
    let (_, dump) = reviewed_and_unreviewed();
    fs::write(root.join(INVENTORY_PATH), "{}\n").expect("write a stale inventory");

    let error = verify_with(&root, &dump, "22.1.8", &scratch_headers(&headers))
        .expect_err("a stale inventory fails verification");
    let message = error.to_string();
    assert!(message.contains("stale"), "{message}");
    assert!(message.contains("api-extract"), "{message}");
}

#[test]
fn a_reviewed_declaration_the_headers_lost_is_named() {
    let headers = ["qgsvectorlayer.h"];
    let root = scratch_repository("lost", &headers, &reviewed_fields());
    // The headers no longer declare QgsVectorLayer::fields, but the manifest
    // still reviews it: that is the staleness the extractor exists to catch.
    let dump = [
        CLASS,
        "| |-AccessSpecDecl 0x2 <line:402:3> col:3 public",
        "| `-CXXMethodDecl 0x3 <line:403:5> col:10 subsetString 'QString () const'",
    ]
    .join("\n");
    let manifest =
        xtask::api_manifest::validate_manifest(&manifest_json(&headers, &reviewed_fields()))
            .expect("fixture manifest is valid");
    let inventory = classify(
        &parse_dump(&dump, &scratch_headers(&headers)),
        &manifest,
        "22.1.8",
    );
    fs::write(root.join(INVENTORY_PATH), render_inventory(&inventory)).expect("write inventory");

    let error = verify_with(&root, &dump, "22.1.8", &scratch_headers(&headers))
        .expect_err("a reviewed declaration that vanished fails verification");
    let message = error.to_string();
    assert!(message.contains("QgsVectorLayer::fields"), "{message}");
    assert!(message.contains("reviewed"), "{message}");
}

#[test]
fn the_scoped_name_key_survives_every_spelling_the_manifest_uses() {
    assert_eq!(
        scoped_name("QgsVectorLayer::fields"),
        "QgsVectorLayer::fields"
    );
    assert_eq!(
        scoped_name("QgsVectorLayer::fields()"),
        "QgsVectorLayer::fields"
    );
    assert_eq!(
        scoped_name("QgsVectorLayer::addFeature(QgsFeature&,QgsFeatureSink::Flags)"),
        "QgsVectorLayer::addFeature"
    );
    assert_eq!(
        scoped_name("QgsVectorLayer::QgsVectorLayer(uri,name,provider)-new"),
        "QgsVectorLayer::QgsVectorLayer"
    );
    assert_eq!(
        scoped_name("QgsVectorLayer::~QgsVectorLayer"),
        "QgsVectorLayer::~QgsVectorLayer"
    );
}
