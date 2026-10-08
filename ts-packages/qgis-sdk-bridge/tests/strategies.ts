/** Domain strategies for transport-facing bridge properties. */

import { jsonValue } from "@qgis/test-utils";
import fc from "fast-check";
import type { QgisLayerInfo } from "@/ts-packages/qgis-sdk-bridge/src/qgis/layers.ts";

/** A compact identifier accepted anywhere the wire expects an opaque id. */
export const qgisIdentifier: fc.Arbitrary<string> = fc.stringMatching(
	/^[A-Za-z][A-Za-z0-9_-]{0,15}$/,
);

/** Human-readable input without constraining the bridge to fixture literals. */
const displayName: fc.Arbitrary<string> = fc.string({
	minLength: 1,
	maxLength: 24,
});

/** JSON object parameters accepted by task and processing facades. */
export const taskParameters: fc.Arbitrary<Record<string, unknown>> =
	fc.dictionary(qgisIdentifier, jsonValue, { maxKeys: 4 });

/** Distinct concurrent task calls, including the parameters sent for each. */
export const concurrentTaskCalls = fc.uniqueArray(
	fc.record({
		name: qgisIdentifier,
		params: taskParameters,
	}),
	{
		minLength: 2,
		maxLength: 5,
		selector: ({ name }) => name,
	},
);

/** A complete vector-layer request and the host answer paired with it. */
export const vectorLayerCall: fc.Arbitrary<{
	path: string;
	name: string;
	provider: string;
	answer: QgisLayerInfo;
}> = fc.record({
	path: fc
		.tuple(qgisIdentifier, fc.constantFrom("gpkg", "shp", "geojson"))
		.map(([base, extension]) => `/data/${base}.${extension}`),
	name: displayName,
	provider: qgisIdentifier,
	answer: fc.record({
		id: qgisIdentifier,
		name: displayName,
		type: fc.constant<"vector">("vector"),
	}),
});

/** A task result, weighted toward falsy values that `||` would corrupt. */
export const taskCompletionResult: fc.Arbitrary<unknown> = fc.oneof(
	fc.constantFrom(null, false, 0, ""),
	jsonValue,
);

/** Two task ids guaranteed not to overlap during event-filtering properties. */
export const distinctTaskIds: fc.Arbitrary<[string, string]> = fc
	.tuple(qgisIdentifier, qgisIdentifier)
	.filter(([own, other]) => own !== other);

/** An ordinary host string that is guaranteed not to parse as JSON. */
export const nonJsonText: fc.Arbitrary<string> = fc
	.string({ maxLength: 32 })
	.map((text) => `not-json:${text}`);
