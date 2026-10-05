/**
 * The QGIS facades, tested through an injected transport.
 *
 * `bridge.test.ts` next door installs globals and drives the whole stack —
 * `QWebChannel`, the loader, the description, the proxy. That is the right
 * shape for testing the *connection*, and the wrong shape for testing
 * `qgis.layers.list()`: a facade takes the raw object in its constructor and
 * never looks at a global, so going through the loader to reach it tests the
 * loader twice and the facade once.
 *
 * These suites inject `harness.target("qgis")` instead, and read
 * `harness.calls` to see what the facade sent. Nothing reaches for
 * `_rawBridge`, `rawQgis` or any other private field: those are names the
 * package may change, while the call a facade makes is the part that is
 * contractual — it is what a Python host on the other side will have to
 * answer.
 *
 * Nothing here opens a socket, waits on a timer, or needs QWebEngine. A task's
 * progress arrives because the test emits it, not because it slept.
 */

import { describe, expect, it } from "bun:test";
import {
	callArgs,
	createBridgeHarness,
	expectCall,
	expectCallbackAndPromise,
	expectDistinctRequestIds,
	expectEventPayloads,
	jsonValue,
	taskProgress,
	wireMethodName,
} from "@qgis/test-utils";
import fc from "fast-check";

import { createBridgeFromDescription } from "../src/description.ts";
import { LayersAPI } from "../src/qgis/layers.ts";
import { MessageAPI } from "../src/qgis/message.ts";
import { NetworkAPI } from "../src/qgis/network.ts";
import { TasksAPI } from "../src/qgis/tasks.ts";
import type { QgisBridge } from "../src/window.ts";

/**
 * The bridge seen from a facade: an `EventTarget` and nothing else.
 *
 * A facade uses its bridge for exactly two things — subscribing to host
 * signals, and a fallback method lookup it must *not* reach when the raw
 * object answers. Passing the harness's own event target therefore covers the
 * first and proves the second: an empty EventTarget has no methods to fall
 * back to, so a test that passes could only have gone through the transport.
 */
const asBridge = (events: EventTarget): QgisBridge =>
	events as unknown as QgisBridge;

describe("Facades over an injected transport", () => {
	it("lists layers by calling the host, not by inspecting internals", async () => {
		const harness = createBridgeHarness();
		harness.replyJson("qgis", "layers_list", [
			{ id: "layer1", name: "Roads", type: "vector" },
		]);
		const layers = new LayersAPI(
			asBridge(harness.events),
			harness.target("qgis"),
		);

		expect(await layers.list()).toEqual([
			{ id: "layer1", name: "Roads", type: "vector" },
		]);
		expectCall(harness, { target: "qgis", method: "layers_list", args: [] });
	});

	it("forwards a facade's arguments to the wire in the declared order", async () => {
		const harness = createBridgeHarness();
		harness.replyJson("qgis", "layers_add_vector", {
			id: "l2",
			name: "Rivers",
		});
		const layers = new LayersAPI(
			asBridge(harness.events),
			harness.target("qgis"),
		);

		await layers.addVector("/data/rivers.shp", "Rivers", "ogr");

		expectCall(harness, {
			target: "qgis",
			method: "layers_add_vector",
			args: ["/data/rivers.shp", "Rivers", "ogr"],
		});
	});

	it("passes a boolean answer through untouched — only strings are parsed", async () => {
		const harness = createBridgeHarness();
		harness.reply("qgis", "message_info", true);
		const message = new MessageAPI(
			asBridge(harness.events),
			harness.target("qgis"),
		);

		expect(await message.info("Title", "Body", 5)).toBe(true);
		expectCall(harness, {
			target: "qgis",
			method: "message_info",
			args: ["Title", "Body", 5],
		});
	});

	it("surfaces a structured host error to the caller", async () => {
		const harness = createBridgeHarness();
		harness.reject(
			"qgis",
			"network_fetch",
			"permission_denied",
			"no net scope",
		);
		const network = new NetworkAPI(
			asBridge(harness.events),
			harness.target("qgis"),
		);

		// The facade wraps the raw call in a promise, so the throw arrives as a
		// rejection with the host's kind intact rather than as a synchronous throw.
		await expect(network.fetch("https://example.com/api")).rejects.toThrow(
			"no net scope",
		);
		// The facade normalises its own defaults before the wire sees them: a
		// bare `fetch(url)` is five positional arguments by the time it leaves.
		expectCall(harness, {
			target: "qgis",
			method: "network_fetch",
			args: ["https://example.com/api", "GET", {}, null, null],
		});
	});

	it("delivers task progress and completion from emitted events, with no sleep", async () => {
		const harness = createBridgeHarness();
		harness.replyJson("qgis", "tasks_run", {
			task_id: "task123",
			status: "queued",
		});
		const tasks = new TasksAPI(
			asBridge(harness.events),
			harness.target("qgis"),
		);

		const task = await tasks.run("buffer_task", { distance: 10 });
		const progress: number[] = [];
		const finished: unknown[] = [];
		task.onProgress((value) => progress.push(value));
		task.onFinished((result) => finished.push(result));

		harness.emit("task_progress", { task_id: "task123", progress: 25 });
		harness.emit("task_progress", { task_id: "other", progress: 99 });
		harness.emit("task_progress", { task_id: "task123", progress: 100 });
		harness.emit("task_finished", { task_id: "task123", result: { ok: true } });

		expectEventPayloads(progress, [25, 100]);
		expectEventPayloads(finished, [{ ok: true }]);
	});

	it("unsubscribes cleanly, so a torn-down listener stops hearing events", async () => {
		const harness = createBridgeHarness();
		harness.replyJson("qgis", "tasks_run", { task_id: "t1" });
		const tasks = new TasksAPI(
			asBridge(harness.events),
			harness.target("qgis"),
		);

		const task = await tasks.run("slow", {});
		const seen: number[] = [];
		const unsubscribe = task.onProgress((value) => seen.push(value));
		harness.emit("task_progress", { task_id: "t1", progress: 10 });
		unsubscribe();
		harness.emit("task_progress", { task_id: "t1", progress: 20 });

		expectEventPayloads(seen, [10]);
	});
});

describe("Properties - what the client owes the transport", () => {
	it("correlates each answer with its own caller, whatever order the host replies in", async () => {
		await fc.assert(
			fc.asyncProperty(
				fc.uniqueArray(fc.string({ minLength: 1, maxLength: 8 }), {
					minLength: 2,
					maxLength: 5,
				}),
				async (names) => {
					const harness = createBridgeHarness();
					const held = harness.hold("qgis", "tasks_run");
					const tasks = new TasksAPI(
						asBridge(harness.events),
						harness.target("qgis"),
					);

					const pending = names.map((name) => tasks.run(name, {}));
					expect(held.length).toBe(names.length);

					// Answer in reverse. A client that matched answers to callers by
					// arrival order would hand every caller the wrong task id.
					for (const entry of [...held].reverse()) {
						entry.respond(
							JSON.stringify({ task_id: `id-${entry.call.args[0]}` }),
						);
					}

					const handles = await Promise.all(pending);
					expect(handles.map((handle) => handle.task_id)).toEqual(
						names.map((name) => `id-${name}`),
					);
					expectDistinctRequestIds(harness);
				},
			),
			{ numRuns: 25 },
		);
	});

	/**
	 * Both sides settle exactly once, and the difference between them is the
	 * decode — not an accident.
	 *
	 * `QgisBridge.call` hands a caller-supplied callback the answer *untouched*
	 * and resolves its promise with the decoded value. That asymmetry is
	 * deliberate (the callback is the QWebChannel-shaped escape hatch), and it
	 * is also easy to regress in either direction, so the property states it:
	 * one callback invocation, one resolution, and `JSON.parse` of the first
	 * equals the second.
	 */
	it("settles callback and promise exactly once, the callback with the raw wire answer", async () => {
		const { createBridge } = await import("../src/window.ts");
		const harness = createBridgeHarness();
		harness.installGlobals();
		try {
			const bridge = (await createBridge("my_bridge")) as unknown as Record<
				string,
				(...args: unknown[]) => Promise<unknown>
			>;

			await fc.assert(
				fc.asyncProperty(jsonValue, async (answer) => {
					harness.replyJson("bridge", "get_layer", answer);
					const { callbackValue, promiseValue } =
						await expectCallbackAndPromise<unknown>((callback) =>
							// biome-ignore lint/style/noNonNullAssertion: the proxy exposes get_layer
							bridge.get_layer!("roads", callback),
						);

					expect(callbackValue).toBe(JSON.stringify(answer));
					expect(promiseValue).toEqual(answer);
				}),
				{ numRuns: 30 },
			);
		} finally {
			harness.restore();
		}
	});

	it("parses a JSON answer and leaves a non-JSON string alone", async () => {
		const harness = createBridgeHarness();
		const layers = new LayersAPI(
			asBridge(harness.events),
			harness.target("qgis"),
		);

		await fc.assert(
			fc.asyncProperty(jsonValue, async (answer) => {
				harness.replyJson("qgis", "layers_list", answer);
				expect(await layers.list()).toEqual(answer as never);
			}),
			{ numRuns: 30 },
		);

		// A string the host did not serialise must survive as that string, not
		// become `undefined` because `JSON.parse` threw.
		harness.reply("qgis", "layers_list", "not json at all");
		expect(await layers.list()).toBe("not json at all" as never);
	});

	it("forwards arbitrary JSON arguments to the wire verbatim", async () => {
		const harness = createBridgeHarness();
		harness.on("qgis", "tasks_run", () => JSON.stringify({ task_id: "t" }));
		const tasks = new TasksAPI(
			asBridge(harness.events),
			harness.target("qgis"),
		);

		await fc.assert(
			fc.asyncProperty(callArgs, async (args) => {
				harness.reset();
				harness.on("qgis", "tasks_run", () => JSON.stringify({ task_id: "t" }));
				await tasks.run("job", args);
				expect(harness.calls.at(-1)?.args).toEqual(["job", args]);
			}),
			{ numRuns: 30 },
		);
	});

	it("rejects a malformed answer only where the contract says it may", async () => {
		const harness = createBridgeHarness();
		const tasks = new TasksAPI(
			asBridge(harness.events),
			harness.target("qgis"),
		);

		// A task answer with no id is malformed; the facade must still produce a
		// handle rather than throwing, because the host owns the id vocabulary
		// and an unknown id is a host bug a client reports, not a crash.
		harness.reply("qgis", "tasks_run", JSON.stringify({}));
		expect((await tasks.run("job", {})).task_id).toBe("unknown");

		// A truncated JSON string is not parsed into nonsense and does not
		// reject either: the decode is best-effort, so the answer stays the
		// string it was and the handle degrades visibly to "unknown".
		harness.reply("qgis", "tasks_run", '{"task_id": "t1"');
		expect((await tasks.run("job", {})).task_id).toBe("unknown");

		// Only a *missing* script is an error, and it names itself.
		harness.reset();
		await expect(tasks.run("job", {})).rejects.toThrow(/no scripted answer/);
	});

	it("exposes exactly the methods a description names, and no others", () => {
		fc.assert(
			fc.property(
				fc.uniqueArray(wireMethodName, { minLength: 1, maxLength: 6 }),
				(names) => {
					const harness = createBridgeHarness({
						descriptions: {
							generated: {
								name: "generated",
								version: "0.1.0",
								methods: names.map((name) => ({
									name,
									args: [],
									arg_types: [],
								})),
								signals: [],
							},
						},
					});
					for (const name of names) {
						harness.reply("generated", name, JSON.stringify({ called: name }));
					}

					const built = createBridgeFromDescription(
						{
							name: "generated",
							version: "0.1.0",
							methods: names.map((name) => ({
								name,
								args: [],
								arg_types: [],
								return_type: "object",
							})),
							signals: [],
						},
						harness.target("generated"),
					) as Record<string, unknown>;

					expect(
						Object.keys(built)
							.filter((key) => typeof built[key] === "function")
							.sort(),
					).toEqual([...names].sort());
				},
			),
			{ numRuns: 30 },
		);
	});

	it("restores every global it installed, whatever was there before", () => {
		const scope = globalThis as unknown as Record<string, unknown>;
		// Whatever this file's other suites left installed is this property's
		// baseline, and is put back at the end: the claim is that a harness
		// restores what it found, not that it empties the scope.
		const outer = {
			present: Object.hasOwn(scope, "QWebChannel"),
			value: scope.QWebChannel,
		};

		fc.assert(
			fc.property(fc.boolean(), (preexisting) => {
				const sentinel = { preexisting };
				if (preexisting) scope.QWebChannel = sentinel;
				else delete scope.QWebChannel;

				const harness = createBridgeHarness();
				harness.installGlobals();
				expect(scope.QWebChannel).not.toBe(sentinel);
				harness.restore();

				if (preexisting) expect(scope.QWebChannel).toBe(sentinel);
				else expect(Object.hasOwn(scope, "QWebChannel")).toBe(false);
			}),
			{ numRuns: 20 },
		);

		if (outer.present) scope.QWebChannel = outer.value;
		else delete scope.QWebChannel;
	});

	it("reports every progress step a host emits, for its own task only", () => {
		fc.assert(
			fc.property(taskProgress, (steps) => {
				const harness = createBridgeHarness();
				const seen: number[] = [];
				const handler = (event: Event) => {
					const detail = (event as CustomEvent).detail;
					if (detail.task_id === "mine") seen.push(detail.progress);
				};
				harness.events.addEventListener("task_progress", handler);

				for (const progress of steps) {
					harness.emit("task_progress", { task_id: "mine", progress });
					harness.emit("task_progress", { task_id: "theirs", progress: 7 });
				}

				expect(seen).toEqual(steps);
			}),
			{ numRuns: 30 },
		);
	});
});
