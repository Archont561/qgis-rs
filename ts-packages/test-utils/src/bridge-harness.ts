/**
 * A scripted bridge transport, and the harness that drives it.
 *
 * `installBridgeGlobals` fakes the *environment* a bridge connects to: a
 * `QWebChannel` constructor, a `qt.webChannelTransport`, two injected
 * descriptions. That is what a loader test needs, and it is more than a facade
 * test needs — `qgis.layers.list()` never touches a global, it calls a method
 * on the raw object it was constructed with.
 *
 * So this file fakes the *transport* instead. `createBridgeHarness()` builds
 * the raw objects a QWebChannel would have handed over, records every call,
 * answers from a script, and hands back an `EventTarget` to emit host events
 * on. A facade test injects `harness.target("qgis")` and asserts against
 * `harness.calls`; nothing reaches for a private field, and nothing has to be
 * restored because nothing process-wide was touched.
 *
 * The two compose: `harness.installGlobals()` publishes *these* scripted
 * objects through `installBridgeGlobals`, so a loader test and a facade test
 * share one script instead of two that can drift, and `harness.restore()`
 * puts every global back.
 */

import type { ScriptedBridgeObject } from "./bridge-globals.ts";
import { installBridgeGlobals } from "./bridge-globals.ts";

/** One call the transport answered, oldest first. */
export interface HarnessCall {
	/** Which scripted object was called — `"bridge"`, `"qgis"`, or a plugin's name. */
	target: string;
	/** The method name, in wire spelling (snake_case). */
	method: string;
	/** The arguments, with QWebChannel's trailing result callback removed. */
	args: unknown[];
	/**
	 * This harness's correlation id, `req-1`, `req-2`, … assigned in call order.
	 *
	 * The QWebChannel wire has no request id — a caller is matched to its answer
	 * by the identity of the callback it was given. That is exactly what makes
	 * out-of-order answers worth testing, and a test cannot state the property
	 * without a name for each call, so the harness supplies one.
	 */
	requestId: string;
}

/** The structured error a rejected call raises on the client side. */
export class BridgeHarnessError extends Error {
	/** The contract's error kind, e.g. `unknown_method` or `permission_denied`. */
	readonly kind: string;
	/** The call that was rejected. */
	readonly call: HarnessCall;

	constructor(kind: string, message: string, call: HarnessCall) {
		super(message);
		this.name = "BridgeHarnessError";
		this.kind = kind;
		this.call = call;
	}
}

/** A scripted answer: whatever the far side would pass to the callback. */
export type HarnessHandler = (call: HarnessCall) => unknown;

/** A call held open by `hold()`, to be answered later. */
export interface HeldCall {
	/** The call that is waiting for an answer. */
	readonly call: HarnessCall;
	/** Answer it now, with `value`. */
	respond(value: unknown): void;
}

export interface BridgeHarnessOptions {
	/**
	 * Target descriptions, keyed by target name. Each one's `methods` decide
	 * which methods the scripted object exposes — a method the description does
	 * not name does not exist, which is the property a proxy test is about.
	 */
	descriptions?: Record<string, HarnessDescription>;
}

/** The description shape the bridge's own loader consumes. */
export interface HarnessDescription {
	name: string;
	version: string;
	methods: { name: string; args: string[]; arg_types: string[] }[];
	signals: { name: string; args: string[]; arg_types: string[] }[];
}

export interface BridgeHarness {
	/** The descriptions this harness was built from, by target name. */
	readonly descriptions: Readonly<Record<string, HarnessDescription>>;
	/** Every call the transport has answered, oldest first. */
	readonly calls: readonly HarnessCall[];
	/** The scripted raw object for `target` — what a QWebChannel would hand over. */
	target(name: string): ScriptedBridgeObject;
	/** An `EventTarget` standing in for the bridge, so facades can subscribe. */
	readonly events: EventTarget;
	/** Script `target.method` to compute its answer from the call. */
	on(target: string, method: string, handler: HarnessHandler): void;
	/** Answer `target.method` with a fixed value, replacing any previous script. */
	reply(target: string, method: string, value: unknown): void;
	/** Answer `target.method` with `JSON.stringify(value)`, as QGIS serialises it. */
	replyJson(target: string, method: string, value: unknown): void;
	/** Make `target.method` raise a structured error instead of answering. */
	reject(target: string, method: string, kind: string, message?: string): void;
	/**
	 * Hold every call to `target.method` open instead of answering it.
	 *
	 * Returns the queue of held calls; respond to them in any order to prove the
	 * client correlates answers by callback rather than by arrival order.
	 */
	hold(target: string, method: string): HeldCall[];
	/** Dispatch a host event on `events`, the way a Python signal arrives. */
	emit(event: string, payload?: unknown): void;
	/** Calls matching a target and, optionally, a method. */
	callsTo(target: string, method?: string): HarnessCall[];
	/** Forget recorded calls and every script, keeping the descriptions. */
	reset(): void;
	/** Undo anything process-wide this harness installed. Idempotent. */
	restore(): void;
	/**
	 * Also install `QWebChannel`, `qt` and the injected descriptions, for tests
	 * that are about the loader rather than about a facade.
	 */
	installGlobals(): ReturnType<typeof installBridgeGlobals>;
}

/** The default two targets: a plugin bridge and the QGIS host object. */
export const DEFAULT_DESCRIPTIONS: Record<string, HarnessDescription> = {
	bridge: {
		name: "my_bridge",
		version: "0.1.0",
		methods: [
			{ name: "get_layer", args: ["layer_id"], arg_types: ["string"] },
			{ name: "log", args: ["msg"], arg_types: ["string"] },
		],
		signals: [
			{ name: "layer_changed", args: ["layer_id"], arg_types: ["string"] },
		],
	},
	qgis: {
		name: "qgis",
		version: "0.1.0",
		methods: [
			{ name: "layers_list", args: [], arg_types: [] },
			{
				name: "layers_add_vector",
				args: ["path", "name", "provider"],
				arg_types: ["string", "string", "string"],
			},
			{
				name: "tasks_run",
				args: ["name", "params"],
				arg_types: ["string", "object"],
			},
			{ name: "tasks_cancel", args: ["task_id"], arg_types: ["string"] },
			{
				name: "message_info",
				args: ["title", "text", "duration"],
				arg_types: ["string", "string", "number"],
			},
			{
				name: "network_fetch",
				args: ["url", "options"],
				arg_types: ["string", "object"],
			},
		],
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
};

/**
 * Widen a harness description into the shape Python injects on `window`.
 *
 * The only difference is `return_type`, which the bridge's loader reads and
 * the harness has no use for: a scripted answer is whatever the script says,
 * not whatever a type name claims.
 */
function toBridgeDescription(
	description: HarnessDescription | undefined,
): unknown {
	if (!description) return null;
	return {
		...description,
		methods: description.methods.map((method) => ({
			return_type: "object",
			...method,
		})),
	};
}

type Script =
	| { kind: "answer"; handler: HarnessHandler }
	| { kind: "reject"; errorKind: string; message: string }
	| { kind: "hold"; queue: HeldCall[] };

/**
 * Build a scripted transport.
 *
 * Nothing is answered by default: an unscripted method throws, naming itself.
 * That is deliberate — a harness that invents plausible answers lets a test
 * pass while asserting against the harness rather than against the client.
 */
export function createBridgeHarness(
	options: BridgeHarnessOptions = {},
): BridgeHarness {
	const descriptions = options.descriptions ?? DEFAULT_DESCRIPTIONS;
	const calls: HarnessCall[] = [];
	const scripts = new Map<string, Script>();
	const events = new EventTarget();
	const installed: ReturnType<typeof installBridgeGlobals>[] = [];
	let nextId = 1;

	const key = (target: string, method: string) => `${target}.${method}`;

	const record = (
		target: string,
		method: string,
		args: unknown[],
	): HarnessCall => {
		const call: HarnessCall = {
			target,
			method,
			args,
			requestId: `req-${nextId++}`,
		};
		calls.push(call);
		return call;
	};

	const scriptedMethod =
		(target: string, method: string) =>
		(...argsWithCallback: unknown[]): void => {
			const callback = argsWithCallback.at(-1);
			if (typeof callback !== "function") {
				throw new Error(
					`${target}.${method} was called without a trailing callback — ` +
						"QWebChannel always appends one, so the client is at fault",
				);
			}
			const call = record(target, method, argsWithCallback.slice(0, -1));
			const script = scripts.get(key(target, method));

			if (script === undefined) {
				throw new Error(
					`no scripted answer for '${target}.${method}' — ` +
						"script it with harness.reply(), replyJson(), on(), reject() or hold()",
				);
			}
			if (script.kind === "reject") {
				throw new BridgeHarnessError(script.errorKind, script.message, call);
			}
			if (script.kind === "hold") {
				script.queue.push({
					call,
					respond: (value) => (callback as (r: unknown) => void)(value),
				});
				return;
			}
			(callback as (r: unknown) => void)(script.handler(call));
		};

	const built = new Map<string, ScriptedBridgeObject>();
	const target = (name: string): ScriptedBridgeObject => {
		const existing = built.get(name);
		if (existing) return existing;
		const description = descriptions[name];
		if (!description) {
			throw new Error(
				`no description for target '${name}' — known targets: ${Object.keys(descriptions).join(", ")}`,
			);
		}
		const object: ScriptedBridgeObject = {};
		for (const method of description.methods) {
			object[method.name] = scriptedMethod(name, method.name);
		}
		built.set(name, object);
		return object;
	};

	return {
		descriptions,
		calls,
		events,
		target,
		on(targetName, method, handler) {
			scripts.set(key(targetName, method), { kind: "answer", handler });
		},
		reply(targetName, method, value) {
			scripts.set(key(targetName, method), {
				kind: "answer",
				handler: () => value,
			});
		},
		replyJson(targetName, method, value) {
			scripts.set(key(targetName, method), {
				kind: "answer",
				handler: () => JSON.stringify(value),
			});
		},
		reject(targetName, method, kind, message) {
			scripts.set(key(targetName, method), {
				kind: "reject",
				errorKind: kind,
				message: message ?? `${targetName}.${method} rejected with ${kind}`,
			});
		},
		hold(targetName, method) {
			const queue: HeldCall[] = [];
			scripts.set(key(targetName, method), { kind: "hold", queue });
			return queue;
		},
		emit(event, payload) {
			events.dispatchEvent(new CustomEvent(event, { detail: payload }));
		},
		callsTo(targetName, method) {
			return calls.filter(
				(call) =>
					call.target === targetName &&
					(method === undefined || call.method === method),
			);
		},
		reset() {
			calls.length = 0;
			scripts.clear();
			nextId = 1;
		},
		restore() {
			// Pop rather than iterate: `restore` is idempotent, and a harness that
			// installed globals twice must undo both, newest first.
			for (let entry = installed.pop(); entry; entry = installed.pop()) {
				entry.restore();
			}
		},
		installGlobals() {
			const entry = installBridgeGlobals({
				objects: { bridge: target("bridge"), qgis: target("qgis") },
				descriptions: {
					bridge: toBridgeDescription(descriptions.bridge),
					qgis: toBridgeDescription(descriptions.qgis),
				},
			});
			installed.push(entry);
			return entry;
		},
	};
}
