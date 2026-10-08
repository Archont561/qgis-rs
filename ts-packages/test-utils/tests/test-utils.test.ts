import { describe, expect, it } from "bun:test";
import fc from "fast-check";

import {
	createFixture,
	installBridgeGlobals,
} from "@/ts-packages/test-utils/src/index.ts";

/** The globals `installBridgeGlobals` owns, as one object so assertions can iterate. */
const OWNED = [
	"QWebChannel",
	"qt",
	"window",
	"__QGIS_BRIDGE_DESCRIPTION__",
	"__QGIS_API_DESCRIPTION__",
] as const;

const scope = globalThis as unknown as Record<string, unknown>;

const call = (fn: unknown, ...args: unknown[]): Promise<unknown> =>
	new Promise((resolve) => {
		(fn as (...a: unknown[]) => void)(...args, resolve);
	});

describe("createFixture", () => {
	it("builds a file fixture at declaration and reuses one value", () => {
		let setups = 0;
		const fixture = createFixture(() => ++setups, undefined, "file");
		expect(fixture.active).toBe(true);
		expect(fixture()).toBe(1);
		expect(fixture()).toBe(1);
		expect(setups).toBe(1);
	});

	it("defers a test fixture until something asks for it", () => {
		let setups = 0;
		const fixture = createFixture(() => ++setups, undefined, "test");
		expect(fixture.active).toBe(false);
		expect(setups).toBe(0);
		expect(fixture()).toBe(1);
		expect(fixture()).toBe(1);
		expect(setups).toBe(1);
	});

	it("survives a missing teardown", () => {
		const fixture = createFixture(() => 1, undefined, "file");
		expect(() => fixture.restore()).not.toThrow();
		expect(fixture.active).toBe(false);
	});
});

describe("installBridgeGlobals", () => {
	const installed = createFixture(
		installBridgeGlobals,
		(value) => value.restore(),
		"file",
	);

	it("installs every global the bridge reads", () => {
		for (const key of OWNED) expect(scope[key]).toBeDefined();
		expect(scope.window).toBe(globalThis);
		expect(
			(scope.qt as { webChannelTransport: unknown })?.webChannelTransport,
		).toBeDefined();
		expect((scope.__QGIS_BRIDGE_DESCRIPTION__ as { name: string }).name).toBe(
			"my_bridge",
		);
		expect((scope.__QGIS_API_DESCRIPTION__ as { name: string }).name).toBe(
			"qgis",
		);
	});

	it("hands the ready callback a channel with both objects, aliased", () => {
		const { channel } = installed();
		expect(typeof channel.objects.bridge.get_layer).toBe("function");
		expect(typeof channel.objects.qgis.layers_list).toBe("function");
		expect(channel.objects.my_bridge).toBe(channel.objects.bridge);
	});

	it("answers on the trailing callback and records the real arguments", async () => {
		const { channel, callLog } = installed();
		// The log is shared by every test in this file; read only this call's entry.
		const before = callLog.length;
		await expect(call(channel.objects.bridge.get_layer, "roads")).resolves.toBe(
			// QGIS serialises across the channel; the bridge parses it back.
			JSON.stringify({ name: "roads", count: 42 }),
		);
		expect(callLog.slice(before)).toEqual([
			{ object: "bridge", method: "get_layer", args: ["roads"] },
		]);
	});

	it("refuses a call that arrives without a callback", () => {
		const { channel } = installed();
		expect(() =>
			(channel.objects.bridge.get_layer as (...args: unknown[]) => void)(
				"roads",
			),
		).toThrow(/without a trailing callback/);
	});

	it("builds only the methods it scripted, so the bridge reports the rest", () => {
		const { channel } = installed();
		expect(Object.keys(channel.objects.bridge).sort()).toEqual([
			"get_layer",
			"layers_add_vector",
			"layers_list",
			"log",
			"message_info",
			"network_fetch",
			"tasks_run",
		]);
		// The bridge's own `call()` turns a missing method into an error naming the
		// alternatives, so an unmethod here is a feature, not a gap.
		expect(channel.objects.qgis.log).toBeUndefined();
	});

	it("lets a suite override one answer", async () => {
		const { channel, setAnswer } = installed();
		setAnswer("qgis", "message_info", false);
		await expect(
			call(channel.objects.qgis.message_info, "t", "m", 1),
		).resolves.toBe(false);
	});
});

describe("installBridgeGlobals — teardown", () => {
	// Test scope, so the fixture below is torn down after each test in this block.
	const installed = createFixture(installBridgeGlobals, (value) =>
		value.restore(),
	);

	it("installs, then is undone by the automatic teardown", () => {
		expect(installed().channel.objects.qgis).toBeDefined();
		expect(scope.__QGIS_BRIDGE_DESCRIPTION__).toBeDefined();
	});

	it("left nothing behind for the next test", () => {
		for (const key of OWNED) expect(scope[key]).toBeUndefined();
	});

	it("is idempotent to restore twice", () => {
		expect(() => installed().restore()).not.toThrow();
		expect(() => installed().restore()).not.toThrow();
	});
});

describe("property-based: the channel is argument-transparent", () => {
	const installed = createFixture(
		installBridgeGlobals,
		(value) => value.restore(),
		"file",
	);

	it("round-trips any layer id verbatim, count fixed", async () => {
		const { channel } = installed();
		await fc.assert(
			fc.asyncProperty(fc.string(), async (id) => {
				await expect(call(channel.objects.bridge.get_layer, id)).resolves.toBe(
					JSON.stringify({ name: id, count: 42 }),
				);
			}),
			{ numRuns: 50 },
		);
	});

	it("defaults an unnamed vector layer to 'Roads'", async () => {
		const { channel } = installed();
		await expect(
			call(channel.objects.qgis.layers_add_vector, "/data/roads.shp"),
		).resolves.toBe(
			JSON.stringify({ id: "layer_new", name: "Roads", type: "vector" }),
		);
	});
});
