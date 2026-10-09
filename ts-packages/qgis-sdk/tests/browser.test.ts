/**
 * The WebEngine global: what a page sees after `<script src="qgis-sdk.js">`.
 *
 * `exposeQgisGlobal` is the seam. It takes the page's window and a factory for the QGIS API,
 * so these tests stand in a plain object for the window and a stub for the bridge. Nothing
 * here touches Qt.
 */

import { describe, expect, it } from "bun:test";

import { exposeQgisGlobal } from "@/browser.ts";
import type { QgisAPI } from "@/qgis.ts";

// A stub: the tests only check identity, so the methods are not needed.
const api = { layers: { list: () => [] } } as unknown as QgisAPI;
const bridge = { name: "bridge" };

describe("exposeQgisGlobal", () => {
	it("does nothing outside a WebEngine page", () => {
		const page: Record<string, unknown> = {};

		const ready = exposeQgisGlobal(
			page,
			async () => ({ bridge, qgis: api }) as any,
		);

		expect(ready).toBeUndefined();
		expect(page.qgis).toBeUndefined();
		expect(page.qgisReady).toBeUndefined();
	});

	it("publishes window.qgis and window.qgisBridge once the bridge is ready", async () => {
		const page: Record<string, any> = { qt: { webChannelTransport: {} } };

		const ready = exposeQgisGlobal(
			page,
			async () => ({ bridge, qgis: api }) as any,
		);

		expect(await ready).toBe(api);
		expect(page.qgis).toBe(api);
		expect(page.qgisBridge).toBe(bridge);
		expect(await page.qgisReady).toBe(api);
	});

	it("treats a page with QWebChannel already loaded as a WebEngine page", async () => {
		const page: Record<string, any> = { QWebChannel: function () {} };

		const ready = exposeQgisGlobal(
			page,
			async () => ({ bridge, qgis: api }) as any,
		);

		expect(await ready).toBe(api);
		expect(page.qgis).toBe(api);
	});

	it("leaves window.qgis unset and rejects qgisReady when the bridge fails", async () => {
		const page: Record<string, any> = { qt: { webChannelTransport: {} } };
		const failure = new Error("no channel");

		const ready = exposeQgisGlobal(page, async () => {
			throw failure;
		});

		await expect(ready).rejects.toBe(failure);
		await expect(page.qgisReady).rejects.toBe(failure);
		expect(page.qgis).toBeUndefined();
	});

	it("publishes one shared channel that the page's scripts and the bridge both use", async () => {
		let built = 0;
		class CountingChannel {
			objects = {};
			constructor(_transport: unknown, onInit: (channel: unknown) => void) {
				built += 1;
				queueMicrotask(() => onInit(this));
			}
		}
		const transport = {};
		const page: Record<string, any> = {
			qt: { webChannelTransport: transport },
			QWebChannel: CountingChannel,
		};
		exposeQgisGlobal(page, async () => ({ bridge, qgis: api }) as any);

		const seen: unknown[] = [];
		page.qgisChannel(transport, (channel: unknown) => seen.push(channel));
		page.qgisChannel(transport, (channel: unknown) => seen.push(channel));
		await new Promise((resolve) => setTimeout(resolve, 0));

		expect(built).toBe(1);
		expect(seen[0]).toBe(seen[1]);
	});
});
