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
	expectCallSequence,
	expectDistinctRequestIds,
	expectEventPayloads,
	jsonValue,
	taskProgress,
	wireMethodName,
} from "@qgis/test-utils";
import fc from "fast-check";

import { createBridgeFromDescription } from "@/ts-packages/qgis-sdk-bridge/src/description.ts";
import { IfaceAPI } from "@/ts-packages/qgis-sdk-bridge/src/qgis/iface.ts";
import { LayersAPI } from "@/ts-packages/qgis-sdk-bridge/src/qgis/layers.ts";
import { MessageAPI } from "@/ts-packages/qgis-sdk-bridge/src/qgis/message.ts";
import { NetworkAPI } from "@/ts-packages/qgis-sdk-bridge/src/qgis/network.ts";
import { ProcessingAPI } from "@/ts-packages/qgis-sdk-bridge/src/qgis/processing.ts";
import { ProjectAPI } from "@/ts-packages/qgis-sdk-bridge/src/qgis/project.ts";
import { SettingsAPI } from "@/ts-packages/qgis-sdk-bridge/src/qgis/settings.ts";
import { TasksAPI } from "@/ts-packages/qgis-sdk-bridge/src/qgis/tasks.ts";
import type { QgisBridge } from "@/ts-packages/qgis-sdk-bridge/src/window.ts";
import {
	concurrentTaskCalls,
	distinctTaskIds,
	nonJsonText,
	qgisIdentifier,
	taskCompletionResult,
	taskParameters,
	vectorLayerCall,
} from "@/ts-packages/qgis-sdk-bridge/tests/strategies.ts";

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

const qgisMethods = [
	["iface_zoom_to_layer", ["id"]],
	["iface_show_message", ["title", "message", "level", "duration"]],
	["iface_active_layer", []],
	["layers_list", []],
	["layers_active", []],
	["layers_add_vector", ["path", "name", "provider"]],
	["layers_add_raster", ["path", "name", "provider"]],
	["layers_remove", ["id"]],
	["layers_zoom_to", ["id"]],
	["layers_set_active", ["id"]],
	["layers_get", ["id"]],
	["message_info", ["title", "message", "duration"]],
	["message_warning", ["title", "message", "duration"]],
	["message_critical", ["title", "message", "duration"]],
	["message_success", ["title", "message", "duration"]],
	["network_fetch", ["url", "method", "headers", "body", "auth_cfg"]],
	["processing_run", ["algorithm_id", "params"]],
	["project_info", []],
	["project_write", []],
	["project_crs", []],
	["project_set_crs", ["auth_id"]],
	["project_path", []],
	["settings_get", ["key", "default"]],
	["settings_set", ["key", "value"]],
	["tasks_run", ["name", "params"]],
	["tasks_list", []],
	["tasks_cancel", ["task_id"]],
] as const;

const createFacadeHarness = () =>
	createBridgeHarness({
		descriptions: {
			qgis: {
				name: "qgis",
				version: "0.1.0",
				methods: qgisMethods.map(([name, args]) => ({
					name,
					args: [...args],
					arg_types: args.map(() => "object"),
				})),
				signals: [
					{
						name: "task_progress",
						args: ["task_id", "progress"],
						arg_types: ["string", "number"],
					},
					{
						name: "task_finished",
						args: ["task_id", "result"],
						arg_types: ["string", "object"],
					},
				],
			},
		},
	});

const addPromiseMethods = (
	harness: ReturnType<typeof createFacadeHarness>,
	methods: readonly string[],
): QgisBridge => {
	const bridge = asBridge(harness.events);
	const promiseMethods = bridge as unknown as Record<
		string,
		(...args: unknown[]) => Promise<unknown>
	>;
	const callbackMethods = harness.target("qgis") as Record<string, unknown>;

	for (const method of methods) {
		promiseMethods[method] = (...args: unknown[]) =>
			new Promise((resolve, reject) => {
				try {
					const callbackMethod = callbackMethods[method];
					if (typeof callbackMethod !== "function") {
						throw new Error(`missing harness method ${method}`);
					}
					callbackMethod(...args, (response: unknown) => {
						if (typeof response === "string") {
							try {
								resolve(JSON.parse(response));
								return;
							} catch {
								// Match QgisBridge.call: non-JSON strings pass through.
							}
						}
						resolve(response);
					});
				} catch (error) {
					reject(error);
				}
			});
	}
	return bridge;
};

describe("Facades over an injected transport", () => {
	it("sends every iface operation with its public defaults", async () => {
		const harness = createFacadeHarness();
		harness.reply("qgis", "iface_zoom_to_layer", true);
		harness.reply("qgis", "iface_show_message", true);
		harness.reply("qgis", "iface_active_layer", '{"id":"raw-string"}');
		const iface = new IfaceAPI(
			asBridge(harness.events),
			harness.target("qgis"),
		);

		expect(await iface.zoomToLayer("roads")).toBe(true);
		expect(await iface.showMessage("Status", "Ready")).toBe(true);
		// iface answers are deliberately not JSON-decoded.
		expect(await iface.activeLayer()).toBe('{"id":"raw-string"}');
		expectCallSequence(harness, [
			{
				target: "qgis",
				method: "iface_zoom_to_layer",
				args: ["roads"],
			},
			{
				target: "qgis",
				method: "iface_show_message",
				args: ["Status", "Ready", 0, 5],
			},
			{ target: "qgis", method: "iface_active_layer", args: [] },
		]);
	});

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

	it("forwards generated facade arguments to the wire in their declared order", async () => {
		await fc.assert(
			fc.asyncProperty(
				vectorLayerCall,
				async ({ path, name, provider, answer }) => {
					const harness = createBridgeHarness();
					harness.replyJson("qgis", "layers_add_vector", answer);
					const layers = new LayersAPI(
						asBridge(harness.events),
						harness.target("qgis"),
					);

					expect(await layers.addVector(path, name, provider)).toEqual(answer);
					expectCall(harness, {
						target: "qgis",
						method: "layers_add_vector",
						args: [path, name, provider],
					});
				},
			),
			{ numRuns: 30 },
		);
	});

	it("sends every layer operation and applies vector and raster defaults", async () => {
		const harness = createFacadeHarness();
		for (const method of [
			"layers_list",
			"layers_active",
			"layers_add_vector",
			"layers_add_raster",
			"layers_remove",
			"layers_zoom_to",
			"layers_set_active",
			"layers_get",
		]) {
			harness.replyJson("qgis", method, { method });
		}
		harness.replyJson("qgis", "layers_get", {
			id: "roads",
			name: "Roads",
			type: "vector",
		});
		const layers = new LayersAPI(
			asBridge(harness.events),
			harness.target("qgis"),
		);

		await layers.list();
		await layers.active();
		await layers.addVector("/data/roads.gpkg");
		await layers.addRaster("/data/elevation.tif");
		await layers.remove("old");
		await layers.zoomTo("roads");
		await layers.setActive("roads");
		expect(await layers.get("roads")).toEqual({
			id: "roads",
			name: "Roads",
			type: "vector",
		});

		expectCallSequence(harness, [
			{ target: "qgis", method: "layers_list", args: [] },
			{ target: "qgis", method: "layers_active", args: [] },
			{
				target: "qgis",
				method: "layers_add_vector",
				args: ["/data/roads.gpkg", "", "ogr"],
			},
			{
				target: "qgis",
				method: "layers_add_raster",
				args: ["/data/elevation.tif", "", "gdal"],
			},
			{ target: "qgis", method: "layers_remove", args: ["old"] },
			{ target: "qgis", method: "layers_zoom_to", args: ["roads"] },
			{ target: "qgis", method: "layers_set_active", args: ["roads"] },
			{ target: "qgis", method: "layers_get", args: ["roads"] },
		]);
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

	it("sends every message operation with duration defaults and coerces callback answers", async () => {
		const harness = createFacadeHarness();
		harness.reply("qgis", "message_info", 0);
		harness.reply("qgis", "message_warning", "");
		harness.reply("qgis", "message_critical", "false");
		harness.reply("qgis", "message_success", { accepted: true });
		const message = new MessageAPI(
			asBridge(harness.events),
			harness.target("qgis"),
		);

		expect(await message.info("Info", "Body")).toBe(false);
		expect(await message.warning("Warning", "Body")).toBe(false);
		expect(await message.critical("Critical", "Body")).toBe(true);
		expect(await message.success("Success", "Body")).toBe(true);
		expectCallSequence(harness, [
			{
				target: "qgis",
				method: "message_info",
				args: ["Info", "Body", 5],
			},
			{
				target: "qgis",
				method: "message_warning",
				args: ["Warning", "Body", 5],
			},
			{
				target: "qgis",
				method: "message_critical",
				args: ["Critical", "Body", 5],
			},
			{
				target: "qgis",
				method: "message_success",
				args: ["Success", "Body", 5],
			},
		]);
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

	it("normalizes network defaults, arguments, and best-effort response helpers", async () => {
		const harness = createFacadeHarness();
		harness.replyJson("qgis", "network_fetch", {
			ok: true,
			status: 201,
			headers: { "content-type": "application/json" },
			url: "https://example.com/final",
			body: '{"created":true}',
		});
		const network = new NetworkAPI(
			asBridge(harness.events),
			harness.target("qgis"),
		);

		const fetched = await network.fetch("https://example.com/items");
		expect(await fetched.text()).toBe('{"created":true}');
		expect(await fetched.json()).toEqual({ created: true });
		await network.get("https://example.com/items", {
			headers: { accept: "application/json" },
			authCfg: "auth-1",
		});
		await network.post("https://example.com/items", "payload", {
			headers: { "content-type": "text/plain" },
		});

		expectCallSequence(harness, [
			{
				target: "qgis",
				method: "network_fetch",
				args: ["https://example.com/items", "GET", {}, null, null],
			},
			{
				target: "qgis",
				method: "network_fetch",
				args: [
					"https://example.com/items",
					"GET",
					{ accept: "application/json" },
					null,
					"auth-1",
				],
			},
			{
				target: "qgis",
				method: "network_fetch",
				args: [
					"https://example.com/items",
					"POST",
					{ "content-type": "text/plain" },
					"payload",
					null,
				],
			},
		]);

		harness.replyJson("qgis", "network_fetch", {
			ok: true,
			status: 200,
			body: "not-json",
		});
		expect(
			await (await network.get("https://example.com/text")).json(),
		).toBeNull();
	});

	it("runs processing with the wire name, ordered arguments, and decoded answer", async () => {
		const harness = createFacadeHarness();
		harness.replyJson("qgis", "processing_run", {
			task_id: "processing-1",
			status: "queued",
		});
		const processing = new ProcessingAPI(
			asBridge(harness.events),
			harness.target("qgis"),
		);

		expect(await processing.run("native:buffer", { DISTANCE: 10 })).toEqual({
			task_id: "processing-1",
			status: "queued",
		});
		expectCall(harness, {
			target: "qgis",
			method: "processing_run",
			args: ["native:buffer", { DISTANCE: 10 }],
		});
	});

	it("sends every project operation and decodes only its JSON callback answers", async () => {
		const harness = createFacadeHarness();
		harness.replyJson("qgis", "project_info", {
			path: "/data/map.qgz",
			crs: "EPSG:4326",
			title: "Map",
		});
		harness.replyJson("qgis", "project_write", true);
		harness.reply("qgis", "project_crs", "EPSG:4326");
		harness.replyJson("qgis", "project_set_crs", true);
		harness.reply("qgis", "project_path", "/data/map.qgz");
		const project = new ProjectAPI(
			asBridge(harness.events),
			harness.target("qgis"),
		);

		expect(await project.info()).toEqual({
			path: "/data/map.qgz",
			crs: "EPSG:4326",
			title: "Map",
		});
		expect(await project.write()).toBe(true);
		expect(await project.crs()).toBe("EPSG:4326");
		expect(await project.setCrs("EPSG:3857")).toBe(true);
		expect(await project.path()).toBe("/data/map.qgz");
		expectCallSequence(harness, [
			{ target: "qgis", method: "project_info", args: [] },
			{ target: "qgis", method: "project_write", args: [] },
			{ target: "qgis", method: "project_crs", args: [] },
			{
				target: "qgis",
				method: "project_set_crs",
				args: ["EPSG:3857"],
			},
			{ target: "qgis", method: "project_path", args: [] },
		]);
	});

	it("sends settings arguments and leaves JSON-looking callback strings untouched", async () => {
		const harness = createFacadeHarness();
		harness.reply("qgis", "settings_get", '{"theme":"dark"}');
		harness.reply("qgis", "settings_set", true);
		const settings = new SettingsAPI(
			asBridge(harness.events),
			harness.target("qgis"),
		);

		expect(await settings.get("ui/theme")).toBe('{"theme":"dark"}');
		expect(await settings.set("ui/theme", "dark")).toBe(true);
		expectCallSequence(harness, [
			{
				target: "qgis",
				method: "settings_get",
				args: ["ui/theme", ""],
			},
			{
				target: "qgis",
				method: "settings_set",
				args: ["ui/theme", "dark"],
			},
		]);
	});

	it("sends every task operation, including handle cancellation and default params", async () => {
		const harness = createFacadeHarness();
		harness.replyJson("qgis", "tasks_run", {
			task_id: "task-1",
			status: "running",
		});
		harness.replyJson("qgis", "tasks_list", [{ task_id: "task-1" }]);
		harness.replyJson("qgis", "tasks_cancel", true);
		const tasks = new TasksAPI(
			asBridge(harness.events),
			harness.target("qgis"),
		);

		const handle = await tasks.run("rebuild-index");
		expect(handle.task_id).toBe("task-1");
		expect(handle.status).toBe("running");
		expect(await tasks.list()).toEqual([{ task_id: "task-1" }]);
		expect(await tasks.cancel("task-2")).toBe(true);
		expect(await handle.cancel()).toBe(true);
		expectCallSequence(harness, [
			{
				target: "qgis",
				method: "tasks_run",
				args: ["rebuild-index", {}],
			},
			{ target: "qgis", method: "tasks_list", args: [] },
			{ target: "qgis", method: "tasks_cancel", args: ["task-2"] },
			{ target: "qgis", method: "tasks_cancel", args: ["task-1"] },
		]);
	});

	it("delivers generated task progress and completion only to their own handle", async () => {
		await fc.assert(
			fc.asyncProperty(
				taskProgress,
				distinctTaskIds,
				taskCompletionResult,
				qgisIdentifier,
				taskParameters,
				async (steps, [taskId, otherId], result, name, params) => {
					const harness = createBridgeHarness();
					harness.replyJson("qgis", "tasks_run", {
						task_id: taskId,
						status: "queued",
					});
					const tasks = new TasksAPI(
						asBridge(harness.events),
						harness.target("qgis"),
					);

					const task = await tasks.run(name, params);
					const progress: number[] = [];
					const finished: unknown[] = [];
					task.onProgress((value) => progress.push(value));
					task.onFinished((value) => finished.push(value));

					for (const value of steps) {
						harness.emit("task_progress", {
							task_id: taskId,
							progress: value,
						});
						harness.emit("task_progress", {
							task_id: otherId,
							progress: value,
						});
					}
					harness.emit("task_finished", { task_id: taskId, result });
					harness.emit("task_finished", { task_id: otherId, result: null });

					expectEventPayloads(progress, steps);
					expectEventPayloads(finished, [result]);
					expectCall(harness, {
						target: "qgis",
						method: "tasks_run",
						args: [name, params],
					});
				},
			),
			{ numRuns: 30 },
		);
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

	it("uses Promise bridge methods when the callback transport lacks an operation", async () => {
		const harness = createFacadeHarness();
		const methods = [
			"iface_active_layer",
			"layers_list",
			"message_info",
			"network_fetch",
			"processing_run",
			"project_crs",
			"settings_get",
			"tasks_list",
		] as const;
		harness.replyJson("qgis", "iface_active_layer", { id: "roads" });
		harness.replyJson("qgis", "layers_list", [
			{ id: "roads", name: "Roads", type: "vector" },
		]);
		harness.reply("qgis", "message_info", true);
		harness.replyJson("qgis", "network_fetch", {
			ok: true,
			status: 200,
			body: "ok",
		});
		harness.replyJson("qgis", "processing_run", { task_id: "p1" });
		harness.reply("qgis", "project_crs", "EPSG:4326");
		harness.reply("qgis", "settings_get", "dark");
		harness.replyJson("qgis", "tasks_list", [{ task_id: "t1" }]);
		const bridge = addPromiseMethods(harness, methods);
		const missingCallbackTransport = {};

		expect(
			await new IfaceAPI(bridge, missingCallbackTransport).activeLayer(),
		).toEqual({ id: "roads" });
		expect(
			await new LayersAPI(bridge, missingCallbackTransport).list(),
		).toEqual([{ id: "roads", name: "Roads", type: "vector" }]);
		expect(
			await new MessageAPI(bridge, missingCallbackTransport).info("T", "M"),
		).toBe(true);
		expect(
			(await new NetworkAPI(bridge, missingCallbackTransport).get("/api"))
				.status,
		).toBe(200);
		expect(
			await new ProcessingAPI(bridge, missingCallbackTransport).run(
				"buffer",
				{},
			),
		).toEqual({ task_id: "p1" });
		expect(await new ProjectAPI(bridge, missingCallbackTransport).crs()).toBe(
			"EPSG:4326",
		);
		expect(
			await new SettingsAPI(bridge, missingCallbackTransport).get("theme"),
		).toBe("dark");
		expect(await new TasksAPI(bridge, missingCallbackTransport).list()).toEqual(
			[{ task_id: "t1" }],
		);
		expectCallSequence(
			harness,
			methods.map((method) => ({
				target: "qgis",
				method,
				args:
					method === "message_info"
						? ["T", "M", 5]
						: method === "network_fetch"
							? ["/api", "GET", {}, null, null]
							: method === "processing_run"
								? ["buffer", {}]
								: method === "settings_get"
									? ["theme", ""]
									: [],
			})),
		);
	});

	it("propagates a rejected Promise bridge method without changing its error", async () => {
		const harness = createFacadeHarness();
		harness.reject(
			"qgis",
			"processing_run",
			"invalid_arguments",
			"distance is required",
		);
		const bridge = addPromiseMethods(harness, ["processing_run"]);
		const processing = new ProcessingAPI(bridge, {});

		await expect(processing.run("buffer", {})).rejects.toThrow(
			"distance is required",
		);
	});
});

describe("Facade behavior without a QGIS transport", () => {
	it("keeps every facade's existing mock values, warnings, and message log", async () => {
		const harness = createFacadeHarness();
		const bridge = asBridge(harness.events);
		const warnings: unknown[][] = [];
		const logs: unknown[][] = [];
		const originalWarn = console.warn;
		const originalLog = console.log;
		console.warn = (...args: unknown[]) => warnings.push(args);
		console.log = (...args: unknown[]) => logs.push(args);

		try {
			const layers = new LayersAPI(bridge, {});
			expect(await layers.list()).toEqual([]);
			expect(await layers.active()).toBeNull();
			expect(await layers.addVector("/data/roads.gpkg")).toBeNull();

			expect(await new IfaceAPI(bridge, {}).zoomToLayer("roads")).toBe(true);
			expect(
				await new ProcessingAPI(bridge, {}).run("native:buffer", {}),
			).toEqual({ task_id: "mock", status: "queued" });

			const project = new ProjectAPI(bridge, {});
			expect(await project.info()).toEqual({ path: "", crs: "", title: "" });
			expect(await project.crs()).toBe("");
			expect(await project.path()).toBe("");
			expect(await project.write()).toBe(true);

			const settings = new SettingsAPI(bridge, {});
			expect(await settings.get("theme", "system")).toBe("system");
			expect(await settings.set("theme", "dark")).toBe(true);

			const tasks = new TasksAPI(bridge, {});
			expect(await tasks.list()).toEqual([]);
			const task = await tasks.run("refresh");
			expect({ task_id: task.task_id, status: task.status }).toEqual({
				task_id: "mock",
				status: "queued",
			});
			expect(await tasks.cancel("task-1")).toBe(true);

			expect(await new MessageAPI(bridge, {}).info("Title", "Body")).toBe(true);
		} finally {
			console.warn = originalWarn;
			console.log = originalLog;
		}

		expect(warnings).toEqual([
			["[qgis.layers] layers_list called without QGIS, returning mock"],
			["[qgis.layers] layers_active called without QGIS, returning mock"],
			["[qgis.layers] layers_add_vector called without QGIS, returning mock"],
			["[qgis.iface] iface_zoom_to_layer mock"],
			["[qgis.processing] processing_run mock"],
			["[qgis.project] project_info mock"],
			["[qgis.project] project_crs mock"],
			["[qgis.project] project_path mock"],
			["[qgis.project] project_write mock"],
			["[qgis.settings] settings_get mock"],
			["[qgis.settings] settings_set mock"],
			["[qgis.tasks] tasks_list mock"],
			["[qgis.tasks] tasks_run mock"],
			["[qgis.tasks] tasks_cancel mock"],
		]);
		expect(logs).toEqual([
			["[qgis.message] message_info:", "Title", "Body", 5],
		]);
	});

	it("keeps the browser-fetch success and error fallback without making a real request", async () => {
		const harness = createFacadeHarness();
		const network = new NetworkAPI(asBridge(harness.events), {});
		const requested: unknown[] = [];
		const warnings: unknown[][] = [];
		const originalFetch = globalThis.fetch;
		const originalWarn = console.warn;
		console.warn = (...args: unknown[]) => warnings.push(args);

		try {
			globalThis.fetch = (async (input: RequestInfo | URL) => {
				requested.push(input);
				return {
					ok: true,
					status: 202,
					headers: new Headers({ "x-source": "browser" }),
					text: async () => "browser body",
				} as Response;
			}) as typeof fetch;
			const response = await network.post(
				"https://example.com/fallback",
				"body",
			);
			expect(response.ok).toBe(true);
			expect(response.status).toBe(202);
			expect(response.headers).toEqual({ "x-source": "browser" });
			expect(await response.text()).toBe("browser body");

			globalThis.fetch = (async () => {
				throw new Error("offline");
			}) as unknown as typeof fetch;
			const failure = await network.get("https://example.com/offline");
			expect(failure.ok).toBe(false);
			expect(failure.status).toBe(0);
			expect(failure.error).toBe("Error: offline");
		} finally {
			globalThis.fetch = originalFetch;
			console.warn = originalWarn;
		}

		expect(requested).toEqual(["https://example.com/fallback"]);
		expect(warnings).toEqual([
			["[qgis.network] network_fetch fallback to browser fetch"],
			["[qgis.network] network_fetch fallback to browser fetch"],
		]);
	});
});

describe("Properties - what the client owes the transport", () => {
	it("correlates each answer with its own caller, whatever order the host replies in", async () => {
		await fc.assert(
			fc.asyncProperty(concurrentTaskCalls, async (calls) => {
				const harness = createBridgeHarness();
				const held = harness.hold("qgis", "tasks_run");
				const tasks = new TasksAPI(
					asBridge(harness.events),
					harness.target("qgis"),
				);

				const pending = calls.map(({ name, params }) =>
					tasks.run(name, params),
				);
				expect(held.length).toBe(calls.length);

				// Answer in reverse. A client that matched answers to callers by
				// arrival order would hand every caller the wrong task id.
				for (const entry of [...held].reverse()) {
					entry.respond(
						JSON.stringify({ task_id: `id-${entry.call.args[0]}` }),
					);
				}

				const handles = await Promise.all(pending);
				expect(handles.map((handle) => handle.task_id)).toEqual(
					calls.map(({ name }) => `id-${name}`),
				);
				expectCallSequence(
					harness,
					calls.map(({ name, params }) => ({
						target: "qgis",
						method: "tasks_run",
						args: [name, params],
					})),
				);
				expectDistinctRequestIds(harness);
			}),
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
		const { createBridge } = await import(
			"@/ts-packages/qgis-sdk-bridge/src/window.ts"
		);
		const harness = createBridgeHarness();
		harness.installGlobals();
		try {
			const bridge = (await createBridge("my_bridge")) as unknown as Record<
				string,
				(...args: unknown[]) => Promise<unknown>
			>;

			await fc.assert(
				fc.asyncProperty(jsonValue, qgisIdentifier, async (answer, layerId) => {
					harness.replyJson("bridge", "get_layer", answer);
					const { callbackValue, promiseValue } =
						await expectCallbackAndPromise<unknown>((callback) =>
							// biome-ignore lint/style/noNonNullAssertion: the proxy exposes get_layer
							bridge.get_layer!(layerId, callback),
						);

					expect(callbackValue).toBe(JSON.stringify(answer));
					expect(promiseValue).toEqual(answer);
					expect(harness.calls.at(-1)?.args).toEqual([layerId]);
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
			fc.asyncProperty(jsonValue, nonJsonText, async (answer, rawText) => {
				harness.replyJson("qgis", "layers_list", answer);
				expect(await layers.list()).toEqual(answer as never);

				// A string the host did not serialise must survive as that string, not
				// become `undefined` because `JSON.parse` threw.
				harness.reply("qgis", "layers_list", rawText);
				expect(await layers.list()).toBe(rawText as never);
			}),
			{ numRuns: 30 },
		);
	});

	it("forwards arbitrary JSON arguments to the wire verbatim", async () => {
		const harness = createBridgeHarness();
		harness.on("qgis", "tasks_run", () => JSON.stringify({ task_id: "t" }));
		const tasks = new TasksAPI(
			asBridge(harness.events),
			harness.target("qgis"),
		);

		await fc.assert(
			fc.asyncProperty(qgisIdentifier, callArgs, async (name, args) => {
				harness.reset();
				harness.on("qgis", "tasks_run", () =>
					JSON.stringify({ task_id: name }),
				);
				await tasks.run(name, args);
				expect(harness.calls.at(-1)?.args).toEqual([name, args]);
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

	it("reports every progress step a host emits, for its own generated task only", () => {
		fc.assert(
			fc.property(taskProgress, distinctTaskIds, (steps, [ownId, otherId]) => {
				const harness = createBridgeHarness();
				const seen: number[] = [];
				const handler = (event: Event) => {
					const detail = (event as CustomEvent).detail;
					if (detail.task_id === ownId) seen.push(detail.progress);
				};
				harness.events.addEventListener("task_progress", handler);

				for (const progress of steps) {
					harness.emit("task_progress", { task_id: ownId, progress });
					harness.emit("task_progress", {
						task_id: otherId,
						progress,
					});
				}

				expect(seen).toEqual(steps);
			}),
			{ numRuns: 30 },
		);
	});
});
