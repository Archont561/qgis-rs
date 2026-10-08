/** qgis.settings API */

import type { QgisBridge } from "../window";
import { QgisTransportAdapter } from "./transport";

interface SettingsOperations {
	settings_get(key: string, defaultValue: string): string;
	settings_set(key: string, value: string): boolean;
}

export class SettingsAPI {
	private readonly transport: QgisTransportAdapter<SettingsOperations>;

	constructor(bridge: QgisBridge, raw: unknown) {
		this.transport = new QgisTransportAdapter(bridge, raw, {
			settings_get: (_key, defaultValue) => {
				console.warn("[qgis.settings] settings_get mock");
				return defaultValue || "";
			},
			settings_set: () => {
				console.warn("[qgis.settings] settings_set mock");
				return true;
			},
		});
	}

	async get(key: string, def = ""): Promise<string> {
		return this.transport.call("settings_get", [key, def]);
	}

	async set(key: string, value: string): Promise<boolean> {
		return this.transport.call("settings_set", [key, value]);
	}
}
