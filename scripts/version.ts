/**
 * The one place the release version is read from, and the one place every
 * published surface is checked against it.
 *
 * `[workspace] version` in the root pixi.toml is the single source of truth.
 * Not Cargo.toml, and not package.json: pixi is the manifest that owns the
 * toolchains, the environments and the tasks, and it is the only manifest that
 * every other one in this repository is downstream of. The Cargo crates, the
 * two Python distributions, the npm packages and the conda packages are then
 * *checked* against pixi's number rather than trusted, because nothing makes
 * nine manifests agree on their own.
 *
 * Callers:
 *   - `pixi run version`        prints it (release workflows compare the tag to it)
 *   - `pixi run version-check`  fails on drift; part of the CI gate
 *   - `pixi run version-set X`  rewrites every manifest that owns a literal
 *
 * Run with bun (the `bun` pixi environment), which is where every other JS tool
 * in this repository already lives.
 */
import { existsSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";

/**
 * Find the workspace manifest by walking up from `startDir`.
 *
 * Anchored on the working directory rather than `import.meta.url` so the module
 * keeps working when a bundler inlines it, and so it behaves the same whether
 * the caller is a pixi task at the repository root or a human in a subdirectory.
 * The `[workspace]` test is what makes "nearest ancestor" safe: the
 * per-distribution pixi.toml manifests under py-packages are package
 * manifests with no workspace table, and picking one of those would silently
 * produce the wrong number.
 */
export function workspaceManifestPath(
	startDir: string = process.cwd(),
): string {
	let dir = resolve(startDir);
	for (;;) {
		const candidate = join(dir, "pixi.toml");
		if (
			existsSync(candidate) &&
			/^\[workspace\]$/m.test(readFileSync(candidate, "utf8"))
		) {
			return candidate;
		}
		const parent = dirname(dir);
		if (parent === dir) {
			throw new Error(
				`no pixi.toml with a [workspace] table at or above ${startDir}`,
			);
		}
		dir = parent;
	}
}

/** The repository root: the directory holding the workspace manifest. */
export function repoRoot(startDir: string = process.cwd()): string {
	return dirname(workspaceManifestPath(startDir));
}

/**
 * Read `version = "..."` out of one named TOML table.
 *
 * Scoped to the table rather than the first `version` key in the file, because
 * every manifest here has several: pixi.toml has `[workspace]` and
 * `[workspace.dependencies]`, and a pyproject.toml has `[project]` plus
 * `[tool.ruff]`, which carries its own `target-version`. A line scan rather
 * than a TOML parser on purpose — one dependency to read one field is a bad
 * trade for a pre-push check.
 */
function versionInTable(manifestPath: string, table: string): string {
	const manifest = readFileSync(manifestPath, "utf8");
	const tablePattern = table.replaceAll(".", "\\.");
	// Anchored on `^[table]$` so `[workspace]` never matches `[workspace.package]`.
	// The `(?:^\[|$(?![\s\S]))` tail lets the last table in a file be read too.
	const body = manifest.match(
		new RegExp(
			`^\\[${tablePattern}\\]$([\\s\\S]*?)(?:^\\[|$(?![\\s\\S]))`,
			"m",
		),
	)?.[1];
	const value = body?.match(/^version\s*=\s*"([^"]+)"/m)?.[1];
	if (!value) throw new Error(`no version in [${table}] of ${manifestPath}`);
	return value;
}

/** `version` out of a `package.json`. */
function npmVersion(packageJsonPath: string): string {
	const parsed = JSON.parse(readFileSync(packageJsonPath, "utf8")) as {
		version?: string;
	};
	if (!parsed.version) throw new Error(`no version in ${packageJsonPath}`);
	return parsed.version;
}

/**
 * Every `qgis-* = { version = "...", path = "..." }` entry in
 * `[workspace.dependencies]` of the root Cargo.toml.
 *
 * Cargo uses the path when building the workspace and substitutes the version
 * when packaging for crates.io, so these numbers are a published surface even
 * though no build ever reads them. A release that bumped the workspace without
 * bumping them would upload crates that ask the registry for their own
 * previous version.
 */
function cargoInternalDependencyVersions(
	root: string,
): { path: string; version: string }[] {
	const manifest = readFileSync(join(root, "Cargo.toml"), "utf8");
	const body =
		manifest.match(
			/^\[workspace\.dependencies\]$([\s\S]*?)(?:^\[|$(?![\s\S]))/m,
		)?.[1] ?? "";
	return [
		...body.matchAll(
			/^(qgis-[a-z]+)\s*=\s*\{[^\n]*version\s*=\s*"([^"]+)"[^\n]*\}/gm,
		),
	].map((match) => ({
		path: `Cargo.toml [workspace.dependencies].${match[1]}`,
		version: match[2] as string,
	}));
}

/** Read `[workspace] version` out of the workspace manifest. */
export function workspaceVersion(startDir: string = process.cwd()): string {
	return versionInTable(workspaceManifestPath(startDir), "workspace");
}

/**
 * Cargo manifests under `crates/` that state a literal version instead of
 * inheriting it.
 *
 * This is an invariant, not a comparison: every crate must say
 * `version.workspace = true`. A hardcoded version in one crate is a copy that
 * the check below would then have to notice, and the entire point of
 * `[workspace.package]` is that there is nothing to notice.
 */
export function hardcodedCargoVersions(
	startDir: string = process.cwd(),
): string[] {
	const root = repoRoot(startDir);
	// A plain readdir rather than a glob helper: this module is also read by
	// tooling that is not bun, and `crates/` is one directory deep by
	// construction (see the header of the root Cargo.toml).
	return readdirSync(join(root, "crates"), { withFileTypes: true })
		.filter((entry) => entry.isDirectory())
		.map((entry) => join(root, "crates", entry.name, "Cargo.toml"))
		.filter((manifest) => existsSync(manifest))
		.sort()
		.filter((manifest) => {
			const body =
				readFileSync(manifest, "utf8").match(
					/^\[package\]$([\s\S]*?)^\[/m,
				)?.[1] ?? "";
			return !/^version\.workspace\s*=\s*true\s*$/m.test(body);
		});
}

/**
 * Every surface that states the version, with paths relative to the repository
 * root so a failure names a file rather than a machine-specific path.
 *
 * The private facade `package.json` files (crates/, py-packages/*, docs/) are
 * in the list on purpose. Publishing is not what makes a version real — being
 * read by someone is, and a manifest carrying a number that nothing compares is
 * exactly the second authority this module exists to prevent.
 */
export function publishedVersions(startDir: string = process.cwd()): {
	expected: string;
	surfaces: { path: string; version: string }[];
} {
	const root = repoRoot(startDir);
	const toml = (path: string, table: string) => ({
		path: `${path} [${table}]`,
		version: versionInTable(join(root, path), table),
	});
	const json = (path: string) => ({
		path,
		version: npmVersion(join(root, path)),
	});
	return {
		expected: workspaceVersion(startDir),
		surfaces: [
			// What every crate inherits, and therefore what `qgis-cli --version`
			// reports (clap reads CARGO_PKG_VERSION).
			toml("Cargo.toml", "workspace.package"),
			// What `pixi publish` stamps into the conda artefact filename and index.
			toml("py-packages/qgis-rs/pixi.toml", "package"),
			toml("py-packages/qgis-sdk/pixi.toml", "package"),
			// What the wheels on PyPI are called.
			toml("py-packages/qgis-rs/pyproject.toml", "project"),
			toml("py-packages/qgis-sdk/pyproject.toml", "project"),
			// What npm publishes.
			json("ts-packages/qgis-node/package.json"),
			json("ts-packages/qgis-sdk-bridge/package.json"),
			// Private, and still checked.
			json("package.json"),
			json("crates/package.json"),
			json("py-packages/qgis-rs/package.json"),
			json("py-packages/qgis-sdk/package.json"),
			json("docs/package.json"),
			// The crates.io versions cargo substitutes for the path dependencies.
			...cargoInternalDependencyVersions(root),
		],
	};
}

/** Replace one literal version in a named TOML table. */
function setTomlVersion(
	manifestPath: string,
	table: string,
	version: string,
): void {
	const manifest = readFileSync(manifestPath, "utf8");
	const tablePattern = table.replaceAll(".", "\\.");
	const pattern = new RegExp(
		`(^\\[${tablePattern}\\]$[\\s\\S]*?^version\\s*=\\s*)"[^"]+"`,
		"m",
	);
	if (!pattern.test(manifest)) {
		throw new Error(`no literal version in [${table}] of ${manifestPath}`);
	}
	writeFileSync(manifestPath, manifest.replace(pattern, `$1"${version}"`));
}

/** Keep the crates.io version of every internal path dependency on the release version. */
function setCargoInternalDependencyVersions(
	root: string,
	version: string,
): void {
	const path = join(root, "Cargo.toml");
	const manifest = readFileSync(path, "utf8");
	writeFileSync(
		path,
		manifest.replace(
			/^(qgis-[a-z]+\s*=\s*\{[^\n]*version\s*=\s*)"[^"]+"/gm,
			`$1"${version}"`,
		),
	);
}

/** Write `version` into a package.json, preserving tab indentation (biome's style here). */
function setNpmVersion(packageJsonPath: string, version: string): void {
	const parsed = JSON.parse(readFileSync(packageJsonPath, "utf8")) as Record<
		string,
		unknown
	>;
	parsed.version = version;
	writeFileSync(packageJsonPath, `${JSON.stringify(parsed, null, "\t")}\n`);
}

/** Rewrite every manifest that owns a literal; the Cargo crates inherit and follow. */
export function setVersion(
	version: string,
	startDir: string = process.cwd(),
): void {
	if (!/^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)$/.test(version)) {
		throw new Error(
			`release version must be stable semver (X.Y.Z), got ${version}`,
		);
	}
	const root = repoRoot(startDir);
	setTomlVersion(join(root, "pixi.toml"), "workspace", version);
	setTomlVersion(join(root, "Cargo.toml"), "workspace.package", version);
	setCargoInternalDependencyVersions(root, version);
	for (const dist of ["qgis-rs", "qgis-sdk"]) {
		setTomlVersion(
			join(root, `py-packages/${dist}/pixi.toml`),
			"package",
			version,
		);
		setTomlVersion(
			join(root, `py-packages/${dist}/pyproject.toml`),
			"project",
			version,
		);
	}
	for (const path of [
		"package.json",
		"crates/package.json",
		"docs/package.json",
		"py-packages/qgis-rs/package.json",
		"py-packages/qgis-sdk/package.json",
		"ts-packages/qgis-node/package.json",
		"ts-packages/qgis-sdk-bridge/package.json",
	]) {
		setNpmVersion(join(root, path), version);
	}
}

/** `--check`: fail if any surface disagrees with the workspace version. */
function check(startDir: string = process.cwd()): number {
	// Checked first: a crate that hardcodes its version is a structural fault,
	// and reporting it as drift would be accurate about the symptom and
	// misleading about the cause.
	const hardcoded = hardcodedCargoVersions(startDir);
	if (hardcoded.length > 0) {
		process.stderr.write(
			"hardcoded Cargo versions (use version.workspace = true):\n",
		);
		for (const manifest of hardcoded) {
			process.stderr.write(`  ${relative(repoRoot(startDir), manifest)}\n`);
		}
		return 1;
	}

	const { expected, surfaces } = publishedVersions(startDir);
	const drifted = surfaces.filter((surface) => surface.version !== expected);
	if (drifted.length === 0) {
		for (const surface of surfaces) {
			process.stdout.write(`${surface.path} ${surface.version}\n`);
		}
		return 0;
	}
	process.stderr.write(`version drift: pixi.toml [workspace] is ${expected}\n`);
	for (const surface of drifted) {
		process.stderr.write(`  ${surface.path} says ${surface.version}\n`);
	}
	process.stderr.write(
		"Run `pixi run version-set <X.Y.Z>` to make every manifest agree.\n",
	);
	return 1;
}

if (import.meta.main) {
	const startDir = process.cwd();
	if (process.argv.includes("--check")) process.exit(check(startDir));

	const setIndex = process.argv.indexOf("--set");
	if (setIndex >= 0) {
		const version = process.argv[setIndex + 1];
		if (!version) {
			process.stderr.write("usage: version.ts --set <X.Y.Z>\n");
			process.exit(2);
		}
		setVersion(version, startDir);
		process.stdout.write(`${version}\n`);
		process.exit(0);
	}

	process.stdout.write(`${workspaceVersion(startDir)}\n`);
}
