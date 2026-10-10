import { defineConfig } from "bunup";

const publicEntries = [
	"src/index.ts",
	"src/react.ts",
	"src/vue.ts",
	"src/svelte.ts",
	"src/webcomponents.ts",
	"src/loader.ts",
	"src/qgis.ts",
	"src/window.ts",
	"src/description.ts",
];

export default defineConfig([
	{
		name: "modules",
		entry: publicEntries,
		outDir: "dist",
		sourceBase: "src",
		format: "esm",
		target: "browser",
		splitting: false,
		preferredTsconfig: "tsconfig.json",
		dts: {
			inferTypes: true,
		},
	},
	{
		name: "commonjs",
		entry: "src/index.ts",
		outDir: "dist",
		sourceBase: "src",
		format: "cjs",
		target: "browser",
		splitting: false,
		preferredTsconfig: "tsconfig.json",
		clean: false,
		dts: false,
	},
]);
