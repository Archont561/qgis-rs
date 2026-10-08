import { dirname, relative, resolve, sep } from "node:path";

const packageRoot = resolve(import.meta.dir, "..");
const declarationsRoot = resolve(packageRoot, "dist");
const aliasPattern = /(["'])@\/ts-packages\/qgis-sdk-bridge\/src\/([^"']+)\1/g;
const declarationFiles = new Bun.Glob("**/*.d.ts");

for await (const declaration of declarationFiles.scan({
	cwd: declarationsRoot,
	onlyFiles: true,
})) {
	const declarationPath = resolve(declarationsRoot, declaration);
	const source = await Bun.file(declarationPath).text();
	const rewritten = source.replace(
		aliasPattern,
		(_match, quote: string, target: string) => {
			const targetPath = resolve(declarationsRoot, target);
			const relativeTarget = relative(dirname(declarationPath), targetPath)
				.split(sep)
				.join("/");
			const specifier = relativeTarget.startsWith(".")
				? relativeTarget
				: `./${relativeTarget}`;
			return `${quote}${specifier}${quote}`;
		},
	);

	if (/["']@\//.test(rewritten)) {
		throw new Error(`failed to rewrite declaration aliases in ${declaration}`);
	}
	if (rewritten !== source) await Bun.write(declarationPath, rewritten);
}
