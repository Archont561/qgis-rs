// The bundled qgis-cli: platform resolution and the runCli boundary.
//
// Resolution is tested with explicit platform inputs, so every supported
// platform is covered on any machine. The binary itself is run only when it has
// been staged for this machine (`bun run build:cli`); QGIS_REQUIRE_NATIVE=1
// turns a missing binary into a failure instead of a skip.

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const cli = require("../src/cli.js");

test("maps each supported platform to its package triple", () => {
	assert.equal(
		cli.cliTriple("linux", "x64", () => false),
		"linux-x64-gnu",
	);
	assert.equal(
		cli.cliTriple("linux", "x64", () => true),
		"linux-x64-musl",
	);
	assert.equal(
		cli.cliTriple("linux", "arm64", () => false),
		"linux-arm64-gnu",
	);
	assert.equal(cli.cliTriple("win32", "x64"), "win32-x64-msvc");
});

test("returns no triple for a platform without a build", () => {
	assert.equal(cli.cliTriple("darwin", "arm64"), null);
	assert.equal(
		cli.cliTriple("linux", "ia32", () => false),
		null,
	);
});

test("refuses an unsupported platform with a message that lists the supported ones", () => {
	assert.throws(
		() => cli.resolveCliBinary({ platform: "darwin", arch: "arm64" }),
		/no build for darwin-arm64\. Supported: linux x64 and arm64/,
	);
});

test("names the platform package when the binary is absent from it", () => {
	// linux-x64-musl ships as a workspace package whose binary is never staged
	// on a glibc machine, so it reaches the "does not contain" branch.
	assert.throws(
		() =>
			cli.resolveCliBinary({
				platform: "linux",
				arch: "x64",
				isMusl: () => true,
			}),
		/@archont561\/qgis-node-linux-x64-musl/,
	);
});

const requireNative = process.env.QGIS_REQUIRE_NATIVE === "1";
const stagedBinary = path.join(
	__dirname,
	"..",
	"npm",
	cli.cliTriple(),
	"bin",
	"qgis-cli",
);
const staged = fs.existsSync(stagedBinary);

test("runs the staged binary and returns its streams", {
	skip:
		!staged &&
		!requireNative &&
		"qgis-cli is not staged; run bun run build:cli",
}, () => {
	assert.ok(staged, `expected ${stagedBinary} — run bun run build:cli`);
	const result = cli.runCli(["--version"]);
	assert.equal(result.exitCode, 0);
	assert.match(result.stdout, /qgis-cli/);
	assert.equal(result.stderr, "");
});

test("reports a failing command through exitCode instead of throwing", {
	skip:
		!staged &&
		!requireNative &&
		"qgis-cli is not staged; run bun run build:cli",
}, () => {
	assert.ok(staged, `expected ${stagedBinary} — run bun run build:cli`);
	const result = cli.runCli(["no-such-subcommand"]);
	assert.notEqual(result.exitCode, 0);
	assert.notEqual(result.stderr, "");
});
