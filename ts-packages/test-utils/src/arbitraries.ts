/**
 * fast-check generators shared by the bridge suites.
 *
 * Every one of these is deliberately *narrower* than the obvious built-in, and
 * the narrowing is the content: a property over `fc.jsonValue()` is a property
 * about the generator, not about the transport. The comments say which detail
 * each one keeps out and why, so the next person widens them on purpose rather
 * than by accident.
 */

import fc from "fast-check";

/**
 * JSON that survives `JSON.parse(JSON.stringify(x))` unchanged.
 *
 * `fc.jsonValue()` emits doubles, and `-0` round-trips to `0`; a property
 * about the bridge should not fail on an IEEE 754 detail. Object keys come
 * from a fixed set for the same reason — a generated `__proto__` tests
 * `JSON.parse`'s prototype handling, not the wire.
 */
export const jsonValue: fc.Arbitrary<unknown> = fc.letrec<{ value: unknown }>(
	(tie) => ({
		value: fc.oneof(
			{ depthSize: "small", maxDepth: 3 },
			fc.string(),
			fc.integer({ min: -1_000_000, max: 1_000_000 }),
			fc.boolean(),
			fc.constant(null),
			fc.array(tie("value"), { maxLength: 4 }),
			fc.dictionary(
				fc.constantFrom("a", "b", "id", "name", "count", "nested"),
				tie("value"),
				{ maxKeys: 4 },
			),
		),
	}),
).value;

/** A wire method name: snake_case, the spelling the contract mandates. */
export const wireMethodName: fc.Arbitrary<string> = fc.stringMatching(
	/^[a-z][a-z0-9_]{0,11}$/,
);

/** The structured error kinds the bridge contract defines. */
export const errorKind: fc.Arbitrary<string> = fc.constantFrom(
	"invalid_arguments",
	"unknown_target",
	"unknown_method",
	"unknown_object",
	"permission_denied",
	"host_unavailable",
);

/**
 * A task's progress run: non-decreasing percentages ending at 100.
 *
 * Non-decreasing because a progress bar that goes backwards is a bug in the
 * host, not a case the client has to tolerate; ending at 100 so a property
 * about "the last progress event precedes completion" has something to say.
 */
export const taskProgress: fc.Arbitrary<number[]> = fc
	.array(fc.integer({ min: 0, max: 100 }), { minLength: 1, maxLength: 6 })
	.map((steps) => [...steps].sort((a, b) => a - b))
	.map((steps) => (steps.at(-1) === 100 ? steps : [...steps, 100]));

/** Arguments a facade might forward: JSON values, never functions. */
export const callArgs: fc.Arbitrary<unknown[]> = fc.array(jsonValue, {
	maxLength: 4,
});
