import { afterAll, afterEach } from "bun:test";

/**
 * How long a fixture's state is meant to last.
 *
 * - `"test"` — set up before each test that touches it, torn down after that test.
 *   The default, and the right choice whenever one test's writes could be visible
 *   to the next.
 * - `"file"` — set up once and torn down after the file. For globals that every
 *   suite in a file reads but none of them mutates; rebuilding them per test would
 *   buy isolation the file does not need at the cost of a setup per test.
 */
export type FixtureScope = "test" | "file";

/** A lazily-initialized fixture. Call it to get the value; setup runs on first call. */
export interface Fixture<T> {
	(): T;
	/** Tear down now. Called automatically by the scope's hook; exposed for explicit use. */
	restore(): void;
	/** Whether the fixture is currently set up. */
	readonly active: boolean;
}

/**
 * Wrap a setup/teardown pair as a fixture whose hooks are registered against the
 * enclosing suite.
 *
 * When the state is built depends on the scope, and the two cases genuinely
 * differ:
 *
 * - `"file"` builds eagerly, at declaration. File-scope state is process-wide
 *   state the tests *assume* rather than call — a global the suite reads directly,
 *   never through the fixture. Deferring its setup to the first fixture call would
 *   mean never setting it up at all.
 * - `"test"` builds lazily, on first call, and is torn down after each test. A
 *   fixture no test in the file touches then costs nothing at all.
 *
 * The teardown hook is registered eagerly either way, because bun requires
 * `afterEach`/`afterAll` to be called while the file's suites are still being
 * collected — long before the first test body runs. A hook registered from inside
 * a test would be too late to bind to anything.
 *
 * @param setup Built once per scope; its return value is handed to every caller.
 * @param teardown Receives the built value. Omit for a fixture with nothing to undo.
 * @param scope `"test"` (default) or `"file"`.
 */
export function createFixture<T>(
	setup: () => T,
	teardown?: (value: T) => void,
	scope: FixtureScope = "test",
): Fixture<T> {
	let built: { value: T } | undefined;

	const restore = (): void => {
		if (built === undefined) return;
		const { value } = built;
		// Cleared before the teardown runs, so a teardown that touches this fixture
		// re-enters setup rather than seeing a value that is already being destroyed.
		built = undefined;
		teardown?.(value);
	};

	if (scope === "file") {
		afterAll(restore);
		built = { value: setup() };
	} else {
		afterEach(restore);
	}

	const fixture = (): T => {
		if (built === undefined) built = { value: setup() };
		return built.value;
	};

	fixture.restore = restore;
	// `Object.defineProperty`, not `Object.assign`: assign *reads* a getter off the
	// source and copies the value it produced, which would freeze `active` at its
	// value on this line and make it permanently wrong.
	Object.defineProperty(fixture, "active", { get: () => built !== undefined });

	return fixture as Fixture<T>;
}
