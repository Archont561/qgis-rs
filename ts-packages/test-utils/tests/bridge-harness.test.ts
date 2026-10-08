/**
 * The harness, tested as the thing other suites will trust.
 *
 * A fake that lies is worse than no fake, so each capability the bridge suites
 * lean on is pinned here: a call is recorded with its arguments and nothing
 * else, an unscripted method refuses rather than inventing an answer, a held
 * call stays open until the test answers it, and `restore()` leaves the
 * process exactly as it found it — including globals that existed *before*
 * the harness ran, which a `delete`-based teardown would silently destroy.
 */

import { describe, expect, it } from "bun:test";
import fc from "fast-check";

import { jsonValue, taskProgress, wireMethodName } from "@/arbitraries.ts";
import {
	expectCall,
	expectCallbackAndPromiseAgree,
	expectCallSequence,
	expectDistinctRequestIds,
	expectErrorKind,
} from "@/assertions.ts";
import {
	BridgeHarnessError,
	createBridgeHarness,
	DEFAULT_DESCRIPTIONS,
} from "@/bridge-harness.ts";

/** The globals `installBridgeGlobals` owns. */
const OWNED = [
	"QWebChannel",
	"qt",
	"window",
	"__QGIS_BRIDGE_DESCRIPTION__",
	"__QGIS_API_DESCRIPTION__",
] as const;

const scope = globalThis as unknown as Record<string, unknown>;

/**
 * What the owned globals look like right now.
 *
 * Asserting "absent after restore" would be wrong rather than strict: another
 * file in this process may legitimately have globals installed around these
 * suites, and the harness's promise is to put back *what it found*, not to
 * leave the scope empty.
 */
const snapshot = (): Map<string, { present: boolean; value: unknown }> =>
	new Map(
		OWNED.map((key) => [
			key,
			{ present: Object.hasOwn(scope, key), value: scope[key] },
		]),
	);

const expectRestoredTo = (
	before: Map<string, { present: boolean; value: unknown }>,
): void => {
	for (const [key, state] of before) {
		expect({
			key,
			present: Object.hasOwn(scope, key),
			value: scope[key],
		}).toEqual({ key, present: state.present, value: state.value });
	}
};

/** Call a scripted method the way QWebChannel does: trailing callback. */
const invoke = (
	object: Record<string, unknown>,
	method: string,
	...args: unknown[]
): Promise<unknown> =>
	new Promise((resolve) => {
		(object[method] as (...a: unknown[]) => void)(...args, resolve);
	});

describe("createBridgeHarness - descriptions and the scripted transport", () => {
	it("exposes exactly the methods its description names", () => {
		const harness = createBridgeHarness();
		const qgis = harness.target("qgis");

		const exposed = Object.keys(qgis).sort();
		const named = DEFAULT_DESCRIPTIONS.qgis?.methods.map((m) => m.name).sort();
		expect(exposed).toEqual(named ?? []);
		expect((qgis as Record<string, unknown>).no_such_method).toBeUndefined();
	});

	it("refuses an unscripted method instead of inventing an answer", () => {
		const harness = createBridgeHarness();
		const qgis = harness.target("qgis");

		expect(() => invoke(qgis, "layers_list")).toThrow(/no scripted answer/);
	});

	it("refuses a target it has no description for", () => {
		const harness = createBridgeHarness();
		expect(() => harness.target("plugin")).toThrow(/no description for target/);
	});

	it("accepts custom descriptions, so a plugin target is just another entry", async () => {
		const harness = createBridgeHarness({
			descriptions: {
				report: {
					name: "report",
					version: "2.0.0",
					methods: [
						{ name: "generate", args: ["format"], arg_types: ["string"] },
					],
					signals: [],
				},
			},
		});
		harness.replyJson("report", "generate", { path: "/tmp/report.pdf" });

		expect(await invoke(harness.target("report"), "generate", "pdf")).toBe(
			JSON.stringify({ path: "/tmp/report.pdf" }),
		);
		expectCall(harness, {
			target: "report",
			method: "generate",
			args: ["pdf"],
		});
	});
});

describe("createBridgeHarness - recording", () => {
	it("records target, method and arguments without the trailing callback", async () => {
		const harness = createBridgeHarness();
		harness.reply("qgis", "message_info", true);

		await invoke(harness.target("qgis"), "message_info", "Title", "Body", 5);

		const call = expectCall(harness, {
			target: "qgis",
			method: "message_info",
			args: ["Title", "Body", 5],
		});
		expect(call.args.some((arg) => typeof arg === "function")).toBe(false);
		expect(call.requestId).toBe("req-1");
	});

	it("rejects a call that arrives without a callback, naming the caller's fault", () => {
		const harness = createBridgeHarness();
		harness.reply("qgis", "layers_list", "[]");
		const qgis = harness.target("qgis") as Record<string, unknown>;

		expect(() => (qgis.layers_list as () => void)()).toThrow(
			/without a trailing callback/,
		);
	});

	it("numbers calls in order, and callsTo filters by target and method", async () => {
		const harness = createBridgeHarness();
		harness.reply("qgis", "layers_list", "[]");
		harness.reply("qgis", "message_info", true);

		await invoke(harness.target("qgis"), "layers_list");
		await invoke(harness.target("qgis"), "message_info", "a", "b", 1);
		await invoke(harness.target("qgis"), "layers_list");

		expect(harness.calls.map((call) => call.requestId)).toEqual([
			"req-1",
			"req-2",
			"req-3",
		]);
		expect(harness.callsTo("qgis", "layers_list").length).toBe(2);
		expect(harness.callsTo("qgis").length).toBe(3);
		expectDistinctRequestIds(harness);
		expectCallSequence(harness, [
			{ target: "qgis", method: "layers_list", args: [] },
			{ target: "qgis", method: "message_info", args: ["a", "b", 1] },
			{ target: "qgis", method: "layers_list", args: [] },
		]);
	});
});

describe("createBridgeHarness - answers, errors and held calls", () => {
	it("computes an answer from the call when scripted with on()", async () => {
		const harness = createBridgeHarness();
		harness.on("qgis", "layers_add_vector", (call) =>
			JSON.stringify({ id: `layer-${call.requestId}`, path: call.args[0] }),
		);

		const answer = await invoke(
			harness.target("qgis"),
			"layers_add_vector",
			"/data/roads.shp",
		);
		expect(JSON.parse(answer as string)).toEqual({
			id: "layer-req-1",
			path: "/data/roads.shp",
		});
	});

	it("raises a structured error for a rejected method", async () => {
		const harness = createBridgeHarness();
		harness.reject("qgis", "layers_list", "permission_denied", "no read scope");

		try {
			await invoke(harness.target("qgis"), "layers_list");
			throw new Error("expected the rejected method to throw");
		} catch (thrown) {
			const error = expectErrorKind(thrown, "permission_denied");
			expect(error.message).toBe("no read scope");
			expect(error.call.method).toBe("layers_list");
		}
	});

	it("holds calls open so they can be answered out of order", async () => {
		const harness = createBridgeHarness();
		const held = harness.hold("qgis", "tasks_run");
		const qgis = harness.target("qgis");

		const first = invoke(qgis, "tasks_run", "alpha", {});
		const second = invoke(qgis, "tasks_run", "beta", {});
		expect(held.length).toBe(2);

		// Answer the second call first: a client that correlated by arrival order
		// rather than by callback identity would hand "beta" to the first caller.
		held[1]?.respond("beta-done");
		held[0]?.respond("alpha-done");

		expect(await first).toBe("alpha-done");
		expect(await second).toBe("beta-done");
		expect(held.map((entry) => entry.call.requestId)).toEqual([
			"req-1",
			"req-2",
		]);
	});

	it("reset forgets calls and scripts but keeps the descriptions", async () => {
		const harness = createBridgeHarness();
		harness.reply("qgis", "layers_list", "[]");
		await invoke(harness.target("qgis"), "layers_list");

		harness.reset();

		expect(harness.calls.length).toBe(0);
		expect(Object.keys(harness.target("qgis")).length).toBeGreaterThan(0);
		expect(() => invoke(harness.target("qgis"), "layers_list")).toThrow(
			/no scripted answer/,
		);
	});
});

describe("createBridgeHarness - globals, installed and restored", () => {
	it("publishes its own scripted objects through installBridgeGlobals", async () => {
		const before = snapshot();
		const harness = createBridgeHarness();
		harness.replyJson("bridge", "get_layer", { name: "Roads" });
		const installed = harness.installGlobals();

		expect(typeof scope.QWebChannel).toBe("function");
		expect(installed.channel.objects.bridge).toBe(harness.target("bridge"));
		expect(installed.channel.objects.my_bridge).toBe(harness.target("bridge"));
		expect((scope.__QGIS_BRIDGE_DESCRIPTION__ as { name: string }).name).toBe(
			"my_bridge",
		);

		// The description the loader reads carries the return_type the bridge's
		// own interface declares, even though the harness has no use for it.
		const methods = (
			scope.__QGIS_BRIDGE_DESCRIPTION__ as {
				methods: { return_type: string }[];
			}
		).methods;
		expect(methods.every((method) => method.return_type === "object")).toBe(
			true,
		);

		await invoke(installed.channel.objects.bridge, "get_layer", "roads");
		expectCall(harness, {
			target: "bridge",
			method: "get_layer",
			args: ["roads"],
		});

		harness.restore();
		expectRestoredTo(before);
	});

	it("restores a global that existed before it, rather than deleting it", () => {
		const outer = snapshot();
		const sentinel = { mine: true };
		scope.__QGIS_BRIDGE_DESCRIPTION__ = sentinel;

		const harness = createBridgeHarness();
		harness.installGlobals();
		expect(scope.__QGIS_BRIDGE_DESCRIPTION__).not.toBe(sentinel);

		harness.restore();
		expect(scope.__QGIS_BRIDGE_DESCRIPTION__).toBe(sentinel);

		// Put the process back the way this test found it, sentinel included.
		const state = outer.get("__QGIS_BRIDGE_DESCRIPTION__");
		if (state?.present) scope.__QGIS_BRIDGE_DESCRIPTION__ = state.value;
		else delete scope.__QGIS_BRIDGE_DESCRIPTION__;
		expectRestoredTo(outer);
	});

	it("restore is idempotent and undoes a double installation", () => {
		const before = snapshot();
		const harness = createBridgeHarness();
		harness.installGlobals();
		harness.installGlobals();

		harness.restore();
		harness.restore();

		expectRestoredTo(before);
	});
});

describe("createBridgeHarness - events", () => {
	it("delivers emitted payloads to subscribers and stops after removal", () => {
		const harness = createBridgeHarness();
		const seen: unknown[] = [];
		const listener = (event: Event) => seen.push((event as CustomEvent).detail);

		harness.events.addEventListener("task_progress", listener);
		harness.emit("task_progress", { task_id: "t1", progress: 25 });
		harness.events.removeEventListener("task_progress", listener);
		harness.emit("task_progress", { task_id: "t1", progress: 50 });

		expect(seen).toEqual([{ task_id: "t1", progress: 25 }]);
	});
});

describe("Properties - the harness keeps its own promises", () => {
	it("records any arguments verbatim, whatever their JSON shape", () => {
		fc.assert(
			fc.property(fc.array(jsonValue, { maxLength: 4 }), (args) => {
				const harness = createBridgeHarness();
				harness.reply("bridge", "log", "ok");
				(harness.target("bridge").log as (...a: unknown[]) => void)(
					...args,
					() => {},
				);
				expect(harness.calls.at(-1)?.args).toEqual(args);
			}),
			{ numRuns: 40 },
		);
	});

	it("gives every call a distinct id, however many are in flight", () => {
		fc.assert(
			fc.property(fc.integer({ min: 1, max: 20 }), (count) => {
				const harness = createBridgeHarness();
				harness.reply("bridge", "log", "ok");
				for (let index = 0; index < count; index += 1) {
					(harness.target("bridge").log as (...a: unknown[]) => void)(
						index,
						() => {},
					);
				}
				expect(harness.calls.length).toBe(count);
				expectDistinctRequestIds(harness);
			}),
			{ numRuns: 30 },
		);
	});

	it("a method name the description does not carry is never callable", () => {
		fc.assert(
			fc.property(wireMethodName, (name) => {
				const harness = createBridgeHarness({
					descriptions: {
						plugin: {
							name: "plugin",
							version: "1.0.0",
							methods: [{ name, args: [], arg_types: [] }],
							signals: [],
						},
					},
				});
				const plugin = harness.target("plugin") as Record<string, unknown>;
				expect(typeof plugin[name]).toBe("function");
				expect(Object.keys(plugin)).toEqual([name]);
			}),
			{ numRuns: 40 },
		);
	});

	it("emits every progress step, in order, with no timer involved", () => {
		fc.assert(
			fc.property(taskProgress, (steps) => {
				const harness = createBridgeHarness();
				const seen: number[] = [];
				harness.events.addEventListener("task_progress", (event) =>
					seen.push((event as CustomEvent).detail.progress),
				);
				for (const progress of steps) {
					harness.emit("task_progress", { task_id: "t1", progress });
				}
				expect(seen).toEqual(steps);
				expect(seen.at(-1)).toBe(100);
			}),
			{ numRuns: 40 },
		);
	});

	it("a rejected method rejects every call to it, with the same kind", async () => {
		const harness = createBridgeHarness();
		await fc.assert(
			fc.asyncProperty(
				fc.constantFrom(
					"unknown_method",
					"host_unavailable",
					"permission_denied",
				),
				async (kind) => {
					harness.reset();
					harness.reject("bridge", "log", kind);
					expect(() =>
						(harness.target("bridge").log as (...a: unknown[]) => void)(
							"x",
							() => {},
						),
					).toThrow(BridgeHarnessError);
				},
			),
			{ numRuns: 20 },
		);
	});
});

describe("Shared assertions", () => {
	it("expectCall names the recorded calls when it cannot find a match", async () => {
		const harness = createBridgeHarness();
		harness.reply("qgis", "layers_list", "[]");
		await invoke(harness.target("qgis"), "layers_list");

		expect(() =>
			expectCall(harness, { target: "qgis", method: "message_info" }),
		).toThrow(
			/expected exactly one call to qgis.message_info[\s\S]*layers_list/,
		);
	});

	it("expectErrorKind refuses a plain Error", () => {
		expect(() => expectErrorKind(new Error("boom"), "unknown_method")).toThrow(
			/expected a BridgeHarnessError of kind 'unknown_method', got Error: boom/,
		);
	});

	it("expectCallbackAndPromiseAgree catches a promise that never settles with the callback's value", async () => {
		const harness = createBridgeHarness();
		harness.reply("bridge", "get_layer", JSON.stringify({ name: "Roads" }));
		const bridge = harness.target("bridge");

		const value = await expectCallbackAndPromiseAgree<unknown>(
			(callback) =>
				new Promise((resolve) => {
					(bridge.get_layer as (...a: unknown[]) => void)(
						"roads",
						(answer: unknown) => {
							callback(answer);
							resolve(answer);
						},
					);
				}),
		);
		expect(value).toBe(JSON.stringify({ name: "Roads" }));
	});
});
