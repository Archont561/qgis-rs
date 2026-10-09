// @archont561/qgis-node is a thin binding over the Rust engine. It ships no command-line
// interface: no bin, no CLI module, no per-platform CLI packages.

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");

test("the package declares no bin", () => {
	const manifest = JSON.parse(read("package.json"));
	assert.equal(manifest.bin, undefined);
	assert.equal(manifest.optionalDependencies, undefined);
});

test("no CLI module, bin shim, staging script or platform packages remain", () => {
	for (const file of ["src/cli.js", "bin", "scripts/stage-cli.js", "npm"]) {
		assert.equal(fs.existsSync(path.join(root, file)), false, file);
	}
});

test("the public module exports no CLI helpers", () => {
	const declarations = read("src/index.d.ts");
	const source = read("src/index.js");
	for (const name of [
		"runCli",
		"resolveCliBinary",
		"CliResult",
		"CliOptions",
	]) {
		assert.equal(declarations.includes(name), false, name);
	}
	assert.equal(source.includes("./cli.js"), false);
});
