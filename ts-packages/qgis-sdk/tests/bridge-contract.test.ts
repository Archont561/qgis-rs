/**
 * The cross-language bridge contract, from the client's side of the wire.
 *
 * These suites read `test-fixtures/bridge/` — the same files as
 * `crates/qgis-protocol/tests/bridge_contract.rs` and
 * `py-packages/qgis-sdk/tests/test_bridge_contract.py`. What the three share is
 * the observable contract and nothing else: no fake implementation class
 * crosses a language boundary, because two sides that agree by being the same
 * code have not agreed about anything.
 *
 * No QWebChannel, no `window`, no globals: the rules asserted here are the ones
 * a client owes the host before any transport exists. Every manifest method
 * becomes exactly one callable path; the wire stays snake_case while the
 * JavaScript surface is camelCase; a response is matched to its call by
 * `request_id` and by nothing else; an event is never mistaken for an answer.
 *
 * `cases.json` is the only list of files, so a vector added there is checked
 * here with no edit to this file.
 */

import { describe, expect, it } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import fc from "fast-check";

const FIXTURES = join(import.meta.dir, "../../../test-fixtures/bridge");
const BRIDGE_VERSION = 1;
const SNAKE_CASE_DOTTED = /^[a-z0-9_]+(\.[a-z0-9_]+)*$/;

/** The small JSON-Schema subset the contract defines (§5). */
interface Schema {
	type?: string;
	properties?: Record<string, Schema>;
	required?: string[];
	items?: Schema;
	enum?: unknown[];
	additional_properties?: boolean;
	$handle?: string;
}

interface MethodEntry {
	name: string;
	call_kind: string;
	permissions: string[];
	args: Schema;
	result: Schema;
}

interface Manifest {
	bridge_version: number;
	namespace: string;
	kind: string;
	version: string;
	methods: MethodEntry[];
	events: { name: string; payload: Schema }[];
}

interface Envelope {
	bridge_version: number;
	request_id?: string;
	target: string;
	method: string;
	args: unknown;
	ok?: boolean;
	result?: unknown;
	error?: { kind: string; message: string; details?: unknown };
	event?: string;
	payload?: unknown;
}

interface Catalogue {
	session_id: string;
	call_kinds: string[];
	error_kinds: string[];
	descriptions: { target: string; kind: string; file: string }[];
	requests: {
		file: string;
		target: string;
		method: string;
		response: string | null;
	}[];
	responses: {
		file: string;
		ok: boolean;
		request_id: string;
		error_kind?: string;
	}[];
	malformed: { file: string; error_kind: string; why: string }[];
	events: {
		file: string;
		target: string;
		event: string;
		correlated: boolean;
	}[];
}

const read = <T>(relative: string): T =>
	JSON.parse(readFileSync(join(FIXTURES, relative), "utf8")) as T;

const cases = read<Catalogue>("cases.json");
const sessionId: string = cases.session_id;
const manifests: Record<string, Manifest> = Object.fromEntries(
	cases.descriptions.map((entry) => [entry.target, read<Manifest>(entry.file)]),
);

/** The rename the client owes the contract: wire `layers.add_vector` is
 * `layers.addVector` in JavaScript, and the wire name is never rewritten. */
const toClientPath = (method: string): string =>
	method
		.split(".")
		.map((segment, index) =>
			index === 0
				? segment
				: segment.replace(/_([a-z0-9])/g, (_, c: string) => c.toUpperCase()),
		)
		.join(".");

const methodSpec = (target: string, name: string): MethodEntry | undefined =>
	manifests[target]?.methods.find((method) => method.name === name);

describe("the manifest is the single source of methods", () => {
	it("describes all four kinds of call", () => {
		const kinds = new Set(
			Object.values(manifests).map((manifest) => manifest.kind),
		);
		expect([...kinds].sort()).toEqual([...cases.call_kinds].sort());
	});

	for (const [target, manifest] of Object.entries(manifests)) {
		it(`${target} names every method once, in snake_case`, () => {
			expect(manifest.bridge_version).toBe(BRIDGE_VERSION);
			expect(target).toMatch(SNAKE_CASE_DOTTED);

			const names = manifest.methods.map((method) => method.name);
			expect(new Set(names).size).toBe(names.length);
			for (const name of names) expect(name).toMatch(SNAKE_CASE_DOTTED);
			for (const event of manifest.events ?? [])
				expect(event.name).toMatch(SNAKE_CASE_DOTTED);
		});

		it(`${target} yields exactly one client path per method`, () => {
			const paths = manifest.methods.map((method) => toClientPath(method.name));
			expect(new Set(paths).size).toBe(paths.length);
			// The rename is one-way cosmetics: nothing the client sends changes.
			for (const method of manifest.methods)
				expect(method.name).toMatch(SNAKE_CASE_DOTTED);
		});
	}
});

describe("envelopes", () => {
	for (const entry of cases.requests) {
		it(`${entry.file} calls a method its target has`, () => {
			const request = read<Envelope>(entry.file);

			expect(request.bridge_version).toBe(BRIDGE_VERSION);
			expect(request.request_id).toBeTruthy();
			expect(request.target).toBe(entry.target);
			expect(request.method).toBe(entry.method);
			expect(Array.isArray(request.args)).toBe(false);
			expect(typeof request.args).toBe("object");
			expect(methodSpec(entry.target, entry.method)).toBeDefined();
		});
	}

	for (const entry of cases.responses) {
		it(`${entry.file} carries exactly what ok promises`, () => {
			const response = read<Envelope>(entry.file);

			expect(response.bridge_version).toBe(BRIDGE_VERSION);
			expect(response.ok).toBe(entry.ok);
			expect(response.request_id).toBe(entry.request_id);

			if (response.ok) {
				expect(response).toHaveProperty("result");
				expect(response.error).toBeUndefined();
			} else {
				expect(response.result).toBeUndefined();
				const error = response.error as { kind: string; message: string };
				expect(error.kind).toBe(entry.error_kind as string);
				expect(cases.error_kinds).toContain(error.kind);
				expect(error.message.length).toBeGreaterThan(0);
			}
		});
	}

	for (const entry of cases.requests.filter((request) => request.response)) {
		it(`${entry.response} is correlated to ${entry.file} by request_id alone`, () => {
			expect(read<Envelope>(entry.response as string).request_id).toBe(
				read<Envelope>(entry.file).request_id,
			);
		});
	}
});

describe("events are not responses", () => {
	for (const entry of cases.events) {
		it(`${entry.file} is announced, not answered`, () => {
			const event = read<Envelope>(entry.file);

			expect(event.ok).toBeUndefined();
			expect(event.result).toBeUndefined();
			expect(event.event).toBe(entry.event);
			expect(event.target).toBe(entry.target);
			expect("request_id" in event).toBe(entry.correlated);

			const declared = (manifests[entry.target] as Manifest).events.map(
				(e) => e.name,
			);
			expect(declared).toContain(event.event as string);
		});
	}
});

describe("refusals a client has to be able to read", () => {
	for (const entry of cases.malformed) {
		it(`${entry.file} is refused with ${entry.error_kind}`, () => {
			// The kinds themselves are decided by the host and proven by the Rust
			// validator; what a client suite can check is that the vector really is
			// the input its catalogue entry claims, so all three languages refuse
			// the same bytes for the same stated reason.
			expect(cases.error_kinds).toContain(entry.error_kind);
			expect(entry.why.length).toBeGreaterThan(0);

			const envelope = read<Envelope>(entry.file);
			switch (entry.error_kind) {
				case "invalid_request":
					expect(
						!("request_id" in envelope) ||
							envelope.bridge_version !== BRIDGE_VERSION ||
							Array.isArray(envelope.args),
					).toBe(true);
					break;
				case "unknown_target":
					expect(manifests[envelope.target]).toBeUndefined();
					break;
				case "unknown_method":
					expect(methodSpec(envelope.target, envelope.method)).toBeUndefined();
					break;
				default:
					expect(methodSpec(envelope.target, envelope.method)).toBeDefined();
			}
		});
	}

	it("a camelCase method name is an unknown method on the wire", () => {
		const envelope = read<Envelope>("malformed/camel-case-method.json");
		expect(methodSpec("qgis", envelope.method)).toBeUndefined();
		// …and it is the camelCase spelling of one that does exist, which is the
		// mistake the rule is there to catch.
		expect(methodSpec("qgis", "layers.add_vector")).toBeDefined();
		expect(toClientPath("layers.add_vector")).toBe(envelope.method);
	});
});

describe("object handles", () => {
	it("are a type and a session, not a parseable string", () => {
		const [layer] = read<{ result: { handle: Record<string, string> }[] }>(
			"responses/qgis-layers-list-success.json",
		).result as [{ handle: Record<string, string> }];

		expect(Object.keys(layer.handle).sort()).toEqual([
			"object_id",
			"object_type",
			"session_id",
		]);
		expect(layer.handle.session_id).toBe(sessionId);
		expect(layer.handle.object_type).toMatch(SNAKE_CASE_DOTTED);
	});

	it("survives the client round trip unchanged, whatever the id is", () => {
		fc.assert(
			fc.property(
				fc.stringMatching(/^[a-z0-9-]{1,24}$/),
				(objectId: string) => {
					const handle = {
						object_id: objectId,
						object_type: "qgis.layer",
						session_id: sessionId,
					};
					expect(JSON.parse(JSON.stringify(handle))).toEqual(handle);
				},
			),
			{ numRuns: 50 },
		);
	});
});

describe("request_id correlation", () => {
	it("is the client's string, echoed and never interpreted", () => {
		fc.assert(
			fc.property(fc.stringMatching(/^[A-Za-z0-9_:-]{1,32}$/), (id: string) => {
				const request = {
					bridge_version: BRIDGE_VERSION,
					request_id: id,
					target: "qgis",
					method: "layers.list",
					args: {},
				};
				const response = {
					bridge_version: BRIDGE_VERSION,
					request_id: JSON.parse(JSON.stringify(request)).request_id,
					ok: true,
					result: [],
				};
				expect(response.request_id).toBe(id);
			}),
			{ numRuns: 50 },
		);
	});
});
