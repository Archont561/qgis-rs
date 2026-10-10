// Script only the native-style binding's JSON answer. The public client
// encodes the request, rejects the version and constructs the actual error.
const test = require("node:test");
const assert = require("node:assert/strict");
const qgis = require("../src/index.js");

for (const [label, received] of [
	["older", 0],
	["newer", 2],
	["missing", undefined],
]) {
	for (const ok of [true, false]) {
		test(`rejects the ${label} response version before its ${ok ? "success" : "failure"} result`, () => {
			const response = {
				ok,
				result: {
					kind: "invalid_extent",
					error: "Do not interpret this result",
				},
			};
			if (received !== undefined) response.transport_version = received;
			const requests = [];
			const binding = {
				invoke(requestJson) {
					requests.push(JSON.parse(requestJson));
					return JSON.stringify(response);
				},
			};

			assert.throws(
				() => qgis.invokeWith(binding, "ping", { value: [1, "two"] }),
				(error) => {
					assert.ok(error instanceof qgis.EngineError);
					assert.equal(error.kind, "unsupported_transport");
					assert.deepEqual(error.detail, {
						supported: qgis.TRANSPORT_VERSION,
						received: received ?? null,
					});
					return true;
				},
			);
			assert.deepEqual(requests, [
				{
					transport_version: qgis.TRANSPORT_VERSION,
					operation: "ping",
					payload: { value: [1, "two"] },
				},
			]);
		});
	}
}
