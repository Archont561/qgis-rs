/**
 * Assertions every bridge suite makes, written once.
 *
 * Each of these replaces a shape that was being spelled out by hand at four or
 * five call sites — "find the last call, destructure it, compare three fields"
 * — and each one fails with a message naming the call it could not find rather
 * than `undefined is not an object`. That is the whole justification: a shared
 * assertion is worth having when it improves the failure, not when it merely
 * shortens the success.
 */

import { expect } from "bun:test";

import type { BridgeHarness, HarnessCall } from "./bridge-harness.ts";
import { BridgeHarnessError } from "./bridge-harness.ts";

/** What a test expects to see on the wire. `args` is compared when given. */
export interface ExpectedCall {
	target: string;
	method: string;
	args?: unknown[];
}

const describeCalls = (calls: readonly HarnessCall[]): string =>
	calls.length === 0
		? "(no calls recorded)"
		: calls
				.map(
					(call) =>
						`  ${call.requestId} ${call.target}.${call.method}(${call.args
							.map((arg) => JSON.stringify(arg))
							.join(", ")})`,
				)
				.join("\n");

/**
 * Assert exactly one call matches, and return it.
 *
 * Returning the call is what makes this composable: a test that also cares
 * about the request id or an argument's shape reads it off the result instead
 * of searching `harness.calls` a second time.
 */
export function expectCall(
	harness: BridgeHarness,
	expected: ExpectedCall,
): HarnessCall {
	const matches = harness
		.callsTo(expected.target, expected.method)
		.filter(
			(call) =>
				expected.args === undefined ||
				JSON.stringify(call.args) === JSON.stringify(expected.args),
		);

	if (matches.length !== 1) {
		const wanted = `${expected.target}.${expected.method}${
			expected.args
				? `(${expected.args.map((a) => JSON.stringify(a)).join(", ")})`
				: ""
		}`;
		throw new Error(
			`expected exactly one call to ${wanted}, found ${matches.length}. Recorded:\n${describeCalls(
				harness.calls,
			)}`,
		);
	}
	// biome-ignore lint/style/noNonNullAssertion: length was just checked to be 1
	return matches[0]!;
}

/** Assert the recorded calls are exactly these, in this order. */
export function expectCallSequence(
	harness: BridgeHarness,
	expected: ExpectedCall[],
): void {
	const actual = harness.calls.map((call) => ({
		target: call.target,
		method: call.method,
		args: call.args,
	}));
	const wanted = expected.map((call) => ({
		target: call.target,
		method: call.method,
		...(call.args === undefined ? {} : { args: call.args }),
	}));
	expect(
		actual.map((call, index) =>
			wanted[index]?.args === undefined
				? { target: call.target, method: call.method }
				: call,
		),
	).toEqual(wanted);
}

/**
 * Assert a call is correlated: every recorded call carries its own request id,
 * and no id repeats.
 *
 * The bridge has no request id on the wire, so this is a statement about the
 * *harness* being able to tell calls apart — which is the precondition for any
 * property about answering them out of order.
 */
export function expectDistinctRequestIds(harness: BridgeHarness): void {
	const ids = harness.calls.map((call) => call.requestId);
	expect(new Set(ids).size).toBe(ids.length);
}

/**
 * Assert `thrown` is a structured bridge error of `kind`.
 *
 * Takes `unknown` because that is what a `catch` binding is, and refuses a
 * plain `Error` on purpose: "the call failed" is not the same claim as "the
 * host answered `permission_denied`".
 */
export function expectErrorKind(
	thrown: unknown,
	kind: string,
): BridgeHarnessError {
	if (!(thrown instanceof BridgeHarnessError)) {
		throw new Error(
			`expected a BridgeHarnessError of kind '${kind}', got ${
				thrown instanceof Error
					? `${thrown.name}: ${thrown.message}`
					: String(thrown)
			}`,
		);
	}
	expect(thrown.kind).toBe(kind);
	return thrown;
}

/** Assert awaiting `call` rejects with a structured error of `kind`. */
export async function expectRejectedKind(
	call: Promise<unknown>,
	kind: string,
): Promise<BridgeHarnessError> {
	try {
		await call;
	} catch (thrown) {
		return expectErrorKind(thrown, kind);
	}
	throw new Error(
		`expected a rejection of kind '${kind}', but the call resolved`,
	);
}

/** Assert an event listener saw exactly these payloads, in order. */
export function expectEventPayloads(
	received: readonly unknown[],
	expected: readonly unknown[],
): void {
	expect(received).toEqual([...expected]);
}

/**
 * Invoke a dual-mode call and report what each side saw.
 *
 * The bridge accepts a trailing callback *and* returns a promise. Both must
 * settle exactly once — an early version forwarded the caller's callback and
 * left the promise pending forever, which turned `await bridge.m(x, cb)` into
 * a hang. Whether the two values are *equal* is a separate question the caller
 * answers, because they are deliberately not equal everywhere: `QgisBridge`
 * hands the callback the raw wire answer and resolves the promise with the
 * decoded one.
 */
export async function expectCallbackAndPromise<T>(
	invoke: (callback: (value: unknown) => void) => Promise<T>,
): Promise<{ callbackValue: unknown; promiseValue: T }> {
	const seen: unknown[] = [];
	const promiseValue = await invoke((value) => seen.push(value));
	expect(seen.length).toBe(1);
	return { callbackValue: seen[0], promiseValue };
}

/** Assert a dual-mode call settles both sides with the same value. */
export async function expectCallbackAndPromiseAgree<T>(
	invoke: (callback: (value: unknown) => void) => Promise<T>,
): Promise<T> {
	const { callbackValue, promiseValue } =
		await expectCallbackAndPromise(invoke);
	expect(callbackValue).toEqual(promiseValue);
	return promiseValue;
}
