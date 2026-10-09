/**
 * The qgis-cli binary shipped with this package, using the Biome model.
 *
 * Each supported platform has its own package, `@archont561/qgis-node-<triple>`,
 * listed in optionalDependencies, so npm installs only the one that matches the
 * machine. That package holds `bin/qgis-cli`. Nothing is downloaded at install
 * or run time, and there is no release URL to trust.
 */

const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const SCOPE = "@archont561/qgis-node";
const COMMAND = "qgis-cli";

/** True when the process runs against musl libc rather than glibc. */
function isMusl() {
	const report = process.report?.getReport?.();
	return (
		report !== undefined && report.header?.glibcVersionRuntime === undefined
	);
}

/**
 * The napi triple naming the platform package for a machine, or null when no
 * package is built for it.
 */
function cliTriple(
	platform = process.platform,
	arch = process.arch,
	musl = isMusl,
) {
	if (platform === "linux" && (arch === "x64" || arch === "arm64")) {
		return `linux-${arch}-${musl() ? "musl" : "gnu"}`;
	}
	if (platform === "win32" && arch === "x64") return "win32-x64-msvc";
	return null;
}

/** Absolute path of the qgis-cli binary for a platform, or a clear error. */
function resolveCliBinary({
	platform = process.platform,
	arch = process.arch,
	isMusl: musl,
} = {}) {
	const triple = cliTriple(platform, arch, musl);
	if (triple === null) {
		throw new Error(
			`qgis-cli has no build for ${platform}-${arch}. Supported: linux x64 and arm64 (glibc and musl), win32 x64.`,
		);
	}
	const pkg = `${SCOPE}-${triple}`;
	let packageDir;
	try {
		packageDir = path.dirname(require.resolve(`${pkg}/package.json`));
	} catch {
		throw new Error(
			`qgis-cli: the platform package ${pkg} is not installed. Reinstall @archont561/qgis-node, and check that your package manager does not skip optional dependencies.`,
		);
	}
	const exe = path.join(
		packageDir,
		"bin",
		platform === "win32" ? `${COMMAND}.exe` : COMMAND,
	);
	if (!fs.existsSync(exe)) {
		throw new Error(
			`qgis-cli: ${pkg} does not contain ${exe}; the package was published without its binary.`,
		);
	}
	return exe;
}

/**
 * Run qgis-cli and capture its output. A failing command is reported through
 * `exitCode`, not thrown: only a binary that cannot start throws.
 */
function runCli(argv = [], options = {}) {
	const exe = resolveCliBinary(options);
	const result = spawnSync(exe, argv, {
		encoding: "utf8",
		windowsHide: true,
		cwd: options.cwd,
	});
	if (result.error) throw result.error;
	return {
		exitCode: result.status ?? 1,
		stdout: result.stdout,
		stderr: result.stderr,
	};
}

/** The bin shim: run qgis-cli with the terminal's streams and return its exit code. */
function main(argv = process.argv.slice(2)) {
	let exe;
	try {
		exe = resolveCliBinary();
	} catch (error) {
		process.stderr.write(`${error.message}\n`);
		return 1;
	}
	const result = spawnSync(exe, argv, { stdio: "inherit", windowsHide: true });
	if (result.error) {
		process.stderr.write(`qgis-cli: ${result.error.message}\n`);
		return 1;
	}
	return result.status ?? 1;
}

module.exports = { cliTriple, resolveCliBinary, runCli, main, COMMAND, SCOPE };
