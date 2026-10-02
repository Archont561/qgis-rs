/**
 * A scripted QWebChannel for testing the bridge without Qt.
 *
 * The bridge's whole contract is "an object on the far side of a QWebChannel
 * answers each method by invoking a trailing callback". That is small enough to
 * fake exactly, and faking it exactly is the point: a stub that resolves on a
 * timer instead of on the callback would pass while testing nothing.
 */

/** One recorded call, in the order the channel received it. */
export interface BridgeCall {
	/** Which of the channel's objects was called. */
	object: "bridge" | "qgis";
	/** The method name on that object. */
	method: string;
	/** The arguments, with any trailing callback removed. */
	args: unknown[];
}

export interface ScriptedBridgeObject {
	[key: string]: unknown;
}

/** What `installBridgeGlobals` puts on the fake `QWebChannel` constructor's callback. */
export interface ScriptedChannel {
	objects: {
		bridge: ScriptedBridgeObject;
		my_bridge: ScriptedBridgeObject;
		qgis: ScriptedBridgeObject;
	};
	transport: unknown;
}

export interface InstalledBridgeGlobals {
	/** The channel the fake `QWebChannel` hands to the bridge. */
	channel: ScriptedChannel;
	/** Every call the channel has answered, oldest first. */
	readonly callLog: readonly BridgeCall[];
	/**
	 * Override one method's answer for the rest of this installation. Pass
	 * `undefined` to fall back to the scripted default.
	 */
	setAnswer(object: "bridge" | "qgis", method: string, answer: unknown): void;
	/** Put back every global this touched. */
	restore(): void;
}

/**
 * A method's answer is whatever the bridge will receive on its callback. Strings
 * are the interesting case: QGIS serialises to JSON over the channel, and the
 * bridge parses a string result before settling, so the defaults below return
 * JSON strings rather than objects.
 */
type Answer = unknown;

function defaultAnswer(
	object: "bridge" | "qgis",
	method: string,
	args: unknown[],
): Answer {
	switch (method) {
		case "get_layer":
			return JSON.stringify({ name: args[0], count: 42 });
		case "log":
			return "ok";
		case "layers_list":
			return JSON.stringify([
				object === "bridge"
					? { id: "layer1", name: "Roads", type: "vector" }
					: { id: "layer1", name: "Roads" },
			]);
		case "layers_add_vector": {
			const [path, name] = args;
			return JSON.stringify({
				id: "layer_new",
				name: name || "Roads",
				type: "vector",
				// The bridge's object echoes the path back; the `qgis` object does not.
				...(object === "bridge" ? { path } : {}),
			});
		}
		case "tasks_run":
			return JSON.stringify({ task_id: "task123", name: args[0] });
		case "message_info":
			return true;
		case "network_fetch":
			return JSON.stringify({
				ok: true,
				status: 200,
				url: args[0],
				body: JSON.stringify({ mock: true }),
				headers: {},
			});
		default:
			throw new Error(
				`installBridgeGlobals: no scripted answer for '${object}.${method}' — ` +
					"register one with setAnswer()",
			);
	}
}

const BRIDGE_METHODS = [
	"get_layer",
	"log",
	"layers_list",
	"layers_add_vector",
	"tasks_run",
	"message_info",
	"network_fetch",
] as const;

const QGIS_METHODS = [
	"layers_list",
	"layers_add_vector",
	"tasks_run",
	"message_info",
	"network_fetch",
] as const;

const BRIDGE_DESCRIPTION = {
	name: "my_bridge",
	version: "0.1.0",
	methods: [
		{
			name: "get_layer",
			args: ["layer_id"],
			arg_types: ["string"],
			return_type: "object",
		},
		{
			name: "log",
			args: ["msg"],
			arg_types: ["string"],
			return_type: "string",
		},
	],
	signals: [
		{ name: "layer_changed", args: ["layer_id"], arg_types: ["string"] },
	],
} as const;

const QGIS_API_DESCRIPTION = {
	name: "qgis",
	version: "0.1.0",
	methods: [
		{ name: "layers_list", args: [], arg_types: [], return_type: "object" },
		{
			name: "layers_add_vector",
			args: ["path", "name", "provider"],
			arg_types: ["string", "string", "string"],
			return_type: "object",
		},
		{
			name: "tasks_run",
			args: ["name", "params"],
			arg_types: ["string", "object"],
			return_type: "object",
		},
		{
			name: "message_info",
			args: ["title", "text", "duration"],
			arg_types: ["string", "string", "number"],
			return_type: "boolean",
		},
		{
			name: "network_fetch",
			args: ["url", "options"],
			arg_types: ["string", "object"],
			return_type: "object",
		},
	],
	signals: [],
} as const;

/**
 * Install `QWebChannel`, `qt`, `window`, `__QGIS_BRIDGE_DESCRIPTION__` and
 * `__QGIS_API_DESCRIPTION__` as globals, and hand back the channel behind them.
 *
 * Always pair this with a teardown — `installBridgeGlobals().restore()` — because
 * these are process-wide. [`createFixture`](./fixture.ts) is the intended way to
 * get that pairing, including across `bun:test`'s file boundaries.
 */
export function installBridgeGlobals(): InstalledBridgeGlobals {
	const scope = globalThis as unknown as Record<string, unknown>;
	const callLog: BridgeCall[] = [];
	const overrides = new Map<string, Answer>();

	const answered = (object: "bridge" | "qgis", method: string) => {
		return (...argsWithCallback: unknown[]): void => {
			// QWebChannel always appends the result callback; it is not an argument
			// the caller passed, so it does not belong in the recorded call, nor in
			// the answer — a scripted answer built from it would serialise a function.
			const callback = argsWithCallback[argsWithCallback.length - 1];
			if (typeof callback !== "function") {
				throw new Error(
					`${object}.${method} was called without a trailing callback`,
				);
			}
			const key = `${object}.${method}`;
			const args = argsWithCallback.slice(0, -1);
			callLog.push({ object, method, args });
			callback(
				overrides.has(key)
					? overrides.get(key)
					: defaultAnswer(object, method, args),
			);
		};
	};

	const build = (
		object: "bridge" | "qgis",
		methods: readonly string[],
	): ScriptedBridgeObject => {
		const built: ScriptedBridgeObject = {};
		for (const method of methods) built[method] = answered(object, method);
		return built;
	};

	const bridge = build("bridge", BRIDGE_METHODS);
	const qgis = build("qgis", QGIS_METHODS);
	const channel: ScriptedChannel = {
		objects: { bridge, my_bridge: bridge, qgis },
		transport: { kind: "scripted" },
	};

	// Record what was there first, so `restore` can put the process back rather
	// than merely deleting keys that may have predated this installation.
	const previous = new Map<string, { present: boolean; value: unknown }>();
	const define = (key: string, value: unknown): void => {
		if (!previous.has(key)) {
			previous.set(key, {
				present: Object.hasOwn(scope, key),
				value: scope[key],
			});
		}
		scope[key] = value;
	};

	class QWebChannelMock {
		constructor(transport: unknown, ready: (channel: ScriptedChannel) => void) {
			// qwebchannel.js calls back synchronously once the transport is up. Doing
			// the same here keeps the bridge's `new QWebChannel(...)` path under test
			// rather than short-circuited by a test-mode branch.
			ready({ ...channel, transport });
		}
	}

	define("QWebChannel", QWebChannelMock);
	define("qt", { webChannelTransport: channel.transport });
	define("window", globalThis);
	define("__QGIS_BRIDGE_DESCRIPTION__", BRIDGE_DESCRIPTION);
	define("__QGIS_API_DESCRIPTION__", QGIS_API_DESCRIPTION);

	let restored = false;

	return {
		channel,
		callLog,
		setAnswer(object, method, answer) {
			overrides.set(`${object}.${method}`, answer);
		},
		restore() {
			if (restored) return;
			restored = true;
			for (const [key, { present, value }] of previous) {
				if (present) {
					scope[key] = value;
				} else {
					delete scope[key];
				}
			}
			previous.clear();
		},
	};
}
