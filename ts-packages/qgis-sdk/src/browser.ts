/**
 * The browser entry, bundled as dist/bundle/qgis-sdk.js and vendored into the Python SDK.
 *
 * A WebEngine page loads it with `<script src="qgis-sdk.js">`, after `qwebchannel.js`. On a
 * WebEngine page it publishes the QGIS API as globals, so plain scripts need no bundler:
 *
 *   window.qgis         the QGIS API (layers, project, message, tasks, network, iface, settings)
 *   window.qgisBridge   the underlying bridge object
 *   window.qgisReady    a promise for `window.qgis`, for code that runs before the channel opens
 *   window.qgisChannel  `(transport, onReady)`: the page's shared QWebChannel. Use it instead of
 *                       `new QWebChannel(...)`, because a second channel on one transport
 *                       takes over the first one's replies.
 *
 * Outside WebEngine nothing is published, so the same page still loads in a normal browser.
 */

import { openChannel } from "@/channel.js";
import { createQgisBridge, type QgisAPI } from "@/qgis.js";

/** Only the parts of the page's window this module reads or writes. */
export interface QgisGlobalTarget {
	qt?: { webChannelTransport?: unknown };
	QWebChannel?: unknown;
	qgis?: unknown;
	qgisBridge?: unknown;
	qgisReady?: Promise<QgisAPI>;
	qgisChannel?: unknown;
}

/** Connects the bridge and publishes the globals; `undefined` when the page is not WebEngine. */
export function exposeQgisGlobal(
	target: QgisGlobalTarget,
	connect: typeof createQgisBridge = createQgisBridge,
): Promise<QgisAPI> | undefined {
	const inWebEngine =
		target.qt?.webChannelTransport !== undefined ||
		target.QWebChannel !== undefined;
	if (!inWebEngine) return undefined;

	// The page's own scripts open the channel through this, so there is never a second one.
	target.qgisChannel = (
		transport: object,
		onReady: (channel: unknown) => void,
	) =>
		openChannel(
			target.QWebChannel as Parameters<typeof openChannel>[0],
			transport,
			onReady,
		);

	const ready = connect().then(({ bridge, qgis }) => {
		target.qgis = qgis;
		target.qgisBridge = bridge;
		return qgis;
	});
	target.qgisReady = ready;
	return ready;
}

export * from "@/index.js";

// Run once per page. The catch only stops an unobserved rejection from being logged twice.
const ready = exposeQgisGlobal(globalThis as QgisGlobalTarget);
ready?.catch((error: unknown) => {
	console.error("[qgis-sdk] could not reach the QGIS bridge", error);
});
