---
id: TASK-32
title: Refactor Python QGIS SDK testing utilities into fixture modules
status: Done
assignee: []
created_date: '2026-10-03 09:16'
updated_date: '2026-10-06 08:15'
labels:
  - testing
  - python
  - qgis-sdk
  - fixtures
milestone: m-4
dependencies:
  - TASK-31
documentation:
  - >-
    backlog/docs/testing/doc-5 -
    QGIS-SDK-Testing-Utilities-and-Cross-Language-Bridge-Contracts.md
  - .knowledge/testing.md
  - .knowledge/qgis-plugin-ui.md
priority: high
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Split qgis_sdk.testing behind compatibility exports into focused fixture modules for environment detection, calls, iface/actions, UI, bridge, network, tasks, processing data, and Hypothesis strategies. Preserve existing fixture names and public fake imports while making pure, Qt, QGIS, and WebEngine execution layers explicit.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Existing qgis_sdk.testing imports and pytest fixture names remain backward compatible.
- [x] #2 A shared Call/CallLog records iface, bridge, network, task, and UI calls through one observable shape.
- [x] #3 FakeNetworkTransport supports scripted replies, failures, redirects, delays, response sequences, and request history without real network access.
- [x] #4 FakeTaskManager models deterministic PENDING/RUNNING/SUCCESS/FAILURE/CANCELED transitions, progress, cancellation, callbacks, chains, and groups.
- [x] #5 BridgeHarness validates request routing and serialization instead of directly exposing arbitrary fake methods.
- [x] #6 Hypothesis strategies cover pure extents, zoom ranges, CRS auth IDs, plugin names, field specs, bridge requests, responses, and task transitions without generating live QGIS objects.
- [x] #7 Pure-Python tests do not initialize Qt or QGIS, and failures to meet a Qt/QGIS prerequisite are explicit skips or prerequisite failures rather than fake fallbacks.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-06: Split py-packages/qgis-sdk/src/qgis_sdk/testing.py (one ~2k-line module) into a package of twelve modules: environment, calls, iface, ui, bridge, qgis_api, network, tasks, processing, data, strategies, plugin. The package __init__ re-exports every legacy name and re-registers every legacy fixture, so AC#1 holds without a shim module.

2026-10-06: AC#1 is proven by tests/test_testing_layers.py, which freezes the legacy surface as data: LEGACY_EXPORTS (about 40 names) must all import from qgis_sdk.testing and LEGACY_FIXTURES (about 35 names) must all be registered with pytest, checked through request._fixturemanager._arg2fixturedefs rather than by calling them. The pre-existing 169-test qgis-sdk suite also still passes unmodified. Facade mechanics worth remembering: pytest 8.4 wraps fixtures in FixtureFunctionDefinition carrying _fixture_function_marker, while older pytest sets _pytestfixturefunction, so _is_fixture() checks both.

2026-10-06: AC#2 Call/CallLog in calls.py record (target, method, args) for the iface, bridge, network, task and UI fakes. Passing calls= to several fakes (fixture shared_calls) puts them in one ordered log, which is what makes cross-fake ordering assertable: paths(), for_target(), for_method(), assert_called(), assert_called_once(), assert_not_called(). The old per-fake lists (iface.messages, manager.requests) are kept. Covered by tests/test_testing_calls.py.

2026-10-06: AC#3 FakeNetworkTransport replaces guessing with scripting: reply(), reply_sequence(repeat_last=), fail(error=/status_code=/raises=), redirect(to=), delay(seconds), and a request history that keeps both url and original_url. An unscripted route raises NoScriptedReply naming the routes that were scripted, an exhausted sequence raises unless repeat_last, and a redirect cycle raises RedirectLoop. Delays advance a virtual clock attribute and set response.elapsed, so nothing sleeps and nothing opens a socket. The permissive FakeNetworkManager mock-true default is untouched for older suites. Covered by tests/test_testing_transport.py.

2026-10-06: AC#4 tasks.py now has an explicit PENDING/RUNNING/SUCCESS/FAILURE/CANCELED machine (ScheduledTask) behind FakeTaskManager(auto_run=False), with run_next()/run_all(), monotonic progress plus progress_history and transitions, cancellation, progress and finished callbacks, group() and chain(). A chain link whose predecessor did not succeed is CANCELED and never run, so TaskChain.state is FAILURE with an observably canceled tail. IllegalTransition guards impossible moves, and canonical_state() maps between this vocabulary and the STARTED/REVOKED names used by the legacy celery-shaped FakeTask/add_task surface. Covered by tests/test_testing_task_machine.py.

2026-10-06: AC#5 BridgeHarness drives the envelope protocol instead of exposing canned methods. It is built from manifests plus handlers keyed by (target, method), and its checks run in the same order the Rust host uses: envelope decode, bridge_version, request_id, target, method, args shape, then unknown_target, unknown_method, permission_denied and argument schema. Foreign or wrongly-typed object handles answer unknown_object, a missing handler answers host_unavailable only for a qgis_host manifest with host_available=False and internal_error otherwise, and a handler may raise HostError(kind, message) to choose its own kind. invoke_json, emit/on_event/events, set_handler, grant/revoke and reset round it out. tests/test_testing_bridge.py (40 tests) drives it from the shared test-fixtures/bridge vectors, including all 12 malformed cases and their catalogued error kinds.

2026-10-06: AC#6 qgis_sdk.testing.strategies adds extents(), zoom_ranges(), crs_auth_ids(), plugin_names(), field_specs(), request_ids(), object_handles(), values_for_schema(), bridge_requests(), bridge_responses(), network_responses() and task_transitions(). Everything is pure data: no strategy constructs a QGIS or Qt object, and the module is the only one allowed to import hypothesis. Covered by tests/test_testing_strategies.py.

2026-10-06: AC#7 environment.py detects the pure / Qt / QGIS / WebEngine layers once per session, and plugin.py skips a test whose layer is missing at collection time (markers pure_python, qt, qgis, webengine, network, tasks) rather than handing it a fake. Two dead ends worth recording. First, AC#7 cannot be asserted by checking sys.modules after importing qgis_sdk.testing: the parent qgis_sdk/__init__.py imports the Qt funnel and the PyQGIS runtime probe, so Qt and qgis.core are already loaded no matter what the testing package does. The honest assertions are an AST scan of every testing module for module-scope imports of PyQt5/PyQt6/PySide6/qgis (and of hypothesis outside strategies.py), plus a subprocess that imports the fakes and asserts QApplication.instance() and QgsApplication.instance() are both None. Second, the pytest Skipped exception derives from BaseException, so pytest.raises(Exception) lets a skip escape and silently skips the asserting test; the layer tests use pytest.raises(pytest.skip.Exception).

2026-10-06: Verified on a simulated pure-Python runtime by running the full suite with a sitecustomize.py meta-path blocker for qgis, PyQt5, PyQt6 and PySide6: 352 passed, 5 skipped, zero failures, with the qgis-marked tests skipping rather than falling back to fakes.

2026-10-06: Docs updated: .knowledge/testing.md gained a section on the package layout and the four new facilities; .knowledge/qgis-plugin-ui.md section 7.3 and the qgis-sdk README now describe CallLog, FakeNetworkTransport, the task state machine, BridgeHarness, the strategies module and collection-time skipping; docs/src/content/docs/reference/testing.mdx gained a module map and reference sections, and docs/src/content/docs/guides/testing-fixtures.mdx gained task-oriented examples for the scripted transport, the manual task manager, the bridge protocol, the shared call log and property-based tests. The Astro docs build passes (49 pages).

2026-10-06: pixi run gates is green: Rust 256 + 22 = 278 tests, ctest 1/1, bun 37 + 82 + 13 = 132, pytest 353 passed / 4 skipped in qgis-sdk (up from 169 / 4) plus 21 in qgis-rs. The 4 skips are the same ones as before this task: two for a missing recorded bridge answer, one for no running QgsApplication, one requiring a pure-Python runtime.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
qgis_sdk.testing is now a package, one module per concern, and the four fakes that could not prove anything have surfaces that can. A shared Call/CallLog gives iface, bridge, network, task and UI fakes one ordered, assertable record. FakeNetworkTransport answers only scripted routes and raises NoScriptedReply otherwise, with sequences, failures, redirects and virtual delays, so no test passes against a URL it never meant to call and nothing sleeps. FakeTaskManager has an explicit PENDING/RUNNING/SUCCESS/FAILURE/CANCELED machine with manual stepping, monotonic progress, chains and groups, so when something ran is finally a question a test can ask. BridgeHarness runs the real envelope protocol in the host check order against the shared test-fixtures/bridge vectors and answers the closed error-kind set. Hypothesis strategies cover pure data only, and the pure / Qt / QGIS / WebEngine layers are explicit: a test whose layer is missing is skipped at collection time, never handed a fake. Every legacy import, fixture name and the pytest11 entry point still work, frozen as data in tests/test_testing_layers.py. qgis-sdk goes from 169 to 353 passing tests with the same 4 skips; pixi run gates is green (Rust 278, pytest 374 passed / 4 skipped, bun 132, ctest 1/1).
<!-- SECTION:FINAL_SUMMARY:END -->
