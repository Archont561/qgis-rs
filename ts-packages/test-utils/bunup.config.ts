import { defineConfig } from "bunup";

export default defineConfig({
	entry: "src/index.ts",
	outDir: "dist",
	sourceBase: "src",
	format: "esm",
	target: "bun",
	splitting: false,
	preferredTsconfig: "tsconfig.json",
	dts: {
		inferTypes: true,
	},
});
