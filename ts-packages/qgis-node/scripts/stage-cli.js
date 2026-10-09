#!/usr/bin/env node
/**
 * Build qgis-cli for this machine and stage it in its platform package, so
 * `bun test` and a local `bunx qgis-cli` can run it. CI builds each platform on
 * its own runner; this script only covers the machine it runs on.
 */

const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const { cliTriple, COMMAND } = require("../src/cli.js");

const packageDir = path.resolve(__dirname, "..");
const repoRoot = path.resolve(packageDir, "../..");
const triple = cliTriple();
if (triple === null) {
	console.error(
		`stage-cli: no qgis-cli platform package for ${process.platform}-${process.arch}`,
	);
	process.exit(1);
}

const build = spawnSync("cargo", ["build", "--release", "-p", "qgis-cli"], {
	cwd: repoRoot,
	stdio: "inherit",
});
if (build.status !== 0) process.exit(build.status ?? 1);

const exeName = process.platform === "win32" ? `${COMMAND}.exe` : COMMAND;
const source = path.join(repoRoot, "target", "release", exeName);
const destinationDir = path.join(packageDir, "npm", triple, "bin");
fs.mkdirSync(destinationDir, { recursive: true });
fs.copyFileSync(source, path.join(destinationDir, exeName));
console.log(`staged ${exeName} in npm/${triple}/bin`);
