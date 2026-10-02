/**
 * The bridge, tested against a scripted QWebChannel rather than against Qt.
 *
 * The channel, `qt`, `window` and both descriptions used to be a hundred lines of
 * module-level assignments at the top of this file, installed once and never taken down. Two
 * things were wrong with that: the globals outlived the suites that needed them, so a suite
 * about `loadDescription` inherited a channel it never touched, and there was no way for a
 * later suite in this process to install its own without first undoing these by hand.
 *
 * They are now `@qgis/test-utils`' `installBridgeGlobals`, wired through `createFixture` in
 * `"file"` scope. File scope because every suite here reads the same descriptions and the
 * channel answers nothing until a test calls it — so per-test freshness would buy isolation
 * this file does not need while costing a rebuild per test. The `restore()` teardown is the
 * part the old version had no answer for: after this file, the process looks the way it did
 * before it ran.
 */

import { describe, expect, it } from "bun:test";
import { createFixture, installBridgeGlobals } from "@qgis/test-utils";

import { loadDescription, loadQgisApiDescription } from "../src/description.ts";
import { QgisBridge } from "../src/window.ts";

const globals = createFixture(
	installBridgeGlobals,
	(installed) => installed.restore(),
	"file",
);

/** The installed channel, for a suite that needs to add an answer or read the call log. */
const channel = createFixture(() => globals().channel, undefined, "file");

describe("QgisBridge - EventTarget/WebSocket-like", () => {
	it("should have WebSocket readyState constants", () => {
		expect(QgisBridge.CONNECTING).toBe(0);
		expect(QgisBridge.OPEN).toBe(1);
		expect(QgisBridge.CLOSING).toBe(2);
		expect(QgisBridge.CLOSED).toBe(3);
	});

	it("should create bridge and open", async () => {
		const { createBridge } = await import("../src/window.ts");
		const bridge = await createBridge("my_bridge");
		expect(bridge.readyState).toBe(QgisBridge.OPEN);
		expect(bridge.objectName).toBe("my_bridge");
	});

	it("should call method via Promise", async () => {
		const { createBridge } = await import("../src/window.ts");
		const bridge = await createBridge("my_bridge");
		const layer = await (bridge as any).get_layer("test_layer");
		expect(layer.name).toBe("test_layer");
		expect(layer.count).toBe(42);
	});

	it("should support EventTarget addEventListener", async () => {
		const { createBridge } = await import("../src/window.ts");
		const bridge = await createBridge("my_bridge");
		let called = false;
		bridge.addEventListener("layer_changed", () => {
			called = true;
		});
		bridge.dispatchEvent(
			new CustomEvent("layer_changed", { detail: { layer_id: "layer1" } }),
		);
		expect(called).toBe(true);
	});

	it("should support onopen/onmessage", async () => {
		const bridge = new QgisBridge("my_bridge");
		let openCalled = false;
		bridge.onopen = () => {
			openCalled = true;
		};
		await bridge._connect();
		expect(openCalled).toBe(true);
		expect(bridge.readyState).toBe(QgisBridge.OPEN);
	});

	it("should load description JSON not codegen", async () => {
		const desc = loadDescription();
		expect(desc).not.toBeNull();
		expect(desc!.name).toBe("my_bridge");
		expect(desc!.methods.length).toBe(2);
	});
});

describe("QgisAPI - complete QGIS Web API", () => {
	it("should load QGIS API description", () => {
		const desc = loadQgisApiDescription();
		expect(desc).not.toBeNull();
		expect(desc!.methods.find((m) => m.name === "layers_list")).toBeDefined();
	});

	it("should create QgisAPI with sub-APIs", async () => {
		const { createQgisBridge } = await import("../src/qgis.ts");
		const { qgis } = await createQgisBridge("my_bridge");
		expect(qgis).toBeDefined();
		expect(qgis.layers).toBeDefined();
		expect(qgis.project).toBeDefined();
		expect(qgis.message).toBeDefined();
		expect(qgis.tasks).toBeDefined();
		expect(qgis.network).toBeDefined();
		expect(qgis.iface).toBeDefined();
		expect(qgis.settings).toBeDefined();
		expect(qgis.processing).toBeDefined();
	});

	it("should list layers via qgis.layers", async () => {
		const { createQgisBridge } = await import("../src/qgis.ts");
		const { qgis } = await createQgisBridge("my_bridge");
		const layers = await qgis.layers.list();
		expect(Array.isArray(layers)).toBe(true);
		// Assert the length before indexing rather than writing `layers[0]!.name`: an empty list
		// is the more likely failure than a sparse one, and saying so gives a better message
		// than "cannot read properties of undefined".
		expect(layers.length).toBeGreaterThan(0);
		expect(layers[0]?.name).toBe("Roads");
	});

	it("should add vector layer via qgis.layers.addVector", async () => {
		const { createQgisBridge } = await import("../src/qgis.ts");
		const { qgis } = await createQgisBridge("my_bridge");
		const layer = await qgis.layers.addVector("/data/roads.shp", "Roads");
		expect(layer.name).toBe("Roads");
		expect(layer.id).toBeDefined();
	});

	it("should run task via qgis.tasks.run", async () => {
		const { createQgisBridge } = await import("../src/qgis.ts");
		const { qgis, bridge } = await createQgisBridge("my_bridge");
		const task = await qgis.tasks.run("buffer_task", { distance: 10 });
		expect(task.task_id).toBe("task123");
		let progressCalled = false;
		task.onProgress(() => {
			progressCalled = true;
		});
		// Simulate progress event from Python
		bridge.dispatchEvent(
			new CustomEvent("task_progress", {
				detail: { task_id: "task123", progress: 50 },
			}),
		);
		expect(progressCalled).toBe(true);
	});

	it("should show message via qgis.message.info", async () => {
		const { createQgisBridge } = await import("../src/qgis.ts");
		const { qgis } = await createQgisBridge("my_bridge");
		const ok = await qgis.message.info("Title", "Hello from JS", 5);
		expect(ok).toBe(true);
	});

	it("should fetch via qgis.network.fetch (QGIS NAM, no CORS)", async () => {
		const { createQgisBridge } = await import("../src/qgis.ts");
		const { qgis } = await createQgisBridge("my_bridge");
		const resp = await qgis.network.fetch("https://example.com/api");
		expect(resp.ok).toBe(true);
	});

	it("should support window.qgis global", async () => {
		const { createQgisBridge } = await import("../src/qgis.ts");
		await createQgisBridge("my_bridge");
		expect((globalThis as any).qgis).toBeDefined();
		expect((globalThis as any).qgis.layers).toBeDefined();
	});

	it("should support EventTarget for qgis", async () => {
		const { createQgisBridge } = await import("../src/qgis.ts");
		const { qgis, bridge } = await createQgisBridge("my_bridge");
		let called = false;
		qgis.addEventListener("layer_added", () => {
			called = true;
		});
		bridge.dispatchEvent(
			new CustomEvent("layer_added", { detail: { id: "layer1" } }),
		);
		// QgisAPI wires bridge signals to qgis, so dispatching on bridge should trigger qgis listener
		expect(called).toBe(true);
		let qgisCalled = false;
		qgis.addEventListener("custom_event", () => {
			qgisCalled = true;
		});
		qgis.dispatchEvent(new CustomEvent("custom_event"));
		expect(qgisCalled).toBe(true);
	});
});

describe("Description loader - no codegen", () => {
	it("should load from window.__QGIS_BRIDGE_DESCRIPTION__", () => {
		const desc = loadDescription();
		expect(desc?.name).toBe("my_bridge");
	});

	it("should create bridge from description", async () => {
		const { createBridgeFromDescription } = await import(
			"../src/description.ts"
		);
		const desc = loadDescription()!;
		const raw = {
			get_layer: (id: string, cb: any) => cb({ name: id }),
			log: (_msg: string, cb: any) => cb("ok"),
		};
		const bridge = createBridgeFromDescription(desc, raw);
		expect(bridge).toBeDefined();
		expect(typeof (bridge as any).get_layer).toBe("function");
	});
});
