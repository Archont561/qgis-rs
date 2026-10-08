/** qgis.network API — via QGIS NAM */

import { QgisTransportAdapter } from "@/ts-packages/qgis-sdk-bridge/src/qgis/transport";
import type { QgisBridge } from "@/ts-packages/qgis-sdk-bridge/src/window";

export interface QgisNetworkResponse {
	ok: boolean;
	status: number;
	headers: Record<string, string>;
	url: string;
	body?: string;
	error?: string;
	text(): Promise<string>;
	json(): Promise<any>;
}

interface NetworkWireResponse {
	ok: boolean;
	status: number;
	headers?: Record<string, string>;
	url?: string;
	body?: string;
	error?: string;
}

interface NetworkOperations {
	network_fetch(
		url: string,
		method: string,
		headers: unknown,
		body: string | null,
		authCfg: string | null,
	): NetworkWireResponse;
}

export class NetworkAPI {
	private readonly transport: QgisTransportAdapter<NetworkOperations>;

	constructor(bridge: QgisBridge, raw: unknown) {
		this.transport = new QgisTransportAdapter(bridge, raw, {
			network_fetch: async (url) => {
				console.warn("[qgis.network] network_fetch fallback to browser fetch");
				try {
					const response = await fetch(url);
					const text = await response.text();
					return {
						status: response.status,
						headers: Object.fromEntries(response.headers.entries()),
						body: text,
						ok: response.ok,
						url,
					};
				} catch (error) {
					return {
						status: 0,
						headers: {},
						body: "",
						ok: false,
						error: String(error),
						url,
					};
				}
			},
		});
	}

	async fetch(
		url: string,
		opts: {
			method?: string;
			headers?: any;
			// `| undefined` rather than optional alone: `post(url, body?)` hands this straight
			// through, and an optional property under `exactOptionalPropertyTypes` may not
			// receive `undefined` explicitly. The value is read as `opts.body || null` below,
			// so "absent" and "undefined" already mean the same thing here.
			body?: string | undefined;
			authCfg?: string | undefined;
		} = {},
	): Promise<QgisNetworkResponse> {
		const res = await this.transport.call(
			"network_fetch",
			[
				url,
				opts.method || "GET",
				opts.headers || {},
				opts.body || null,
				opts.authCfg || null,
			],
			{ callbackResponse: "json" },
		);

		return {
			ok: res.ok,
			status: res.status,
			headers: res.headers || {},
			url: res.url || url,
			body: res.body,
			error: res.error,
			text: async () => res.body || "",
			json: async () => {
				try {
					return JSON.parse(res.body || "{}");
				} catch {
					return null;
				}
			},
		} as QgisNetworkResponse;
	}

	async get(
		url: string,
		opts: { headers?: any; authCfg?: string | undefined } = {},
	): Promise<QgisNetworkResponse> {
		return this.fetch(url, { method: "GET", ...opts });
	}

	async post(
		url: string,
		body?: string,
		opts: { headers?: any; authCfg?: string | undefined } = {},
	): Promise<QgisNetworkResponse> {
		return this.fetch(url, { method: "POST", body, ...opts });
	}
}
