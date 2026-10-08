/** qgis.iface API */

import type { QgisBridge } from "../window";
import { QgisTransportAdapter } from "./transport";

interface IfaceOperations {
	iface_zoom_to_layer(id: string): boolean;
	iface_show_message(
		title: string,
		message: string,
		level: number,
		duration: number,
	): boolean;
	iface_active_layer(): unknown;
}

export class IfaceAPI {
	private readonly transport: QgisTransportAdapter<IfaceOperations>;

	constructor(bridge: QgisBridge, raw: unknown) {
		this.transport = new QgisTransportAdapter(bridge, raw, {
			iface_zoom_to_layer: () => {
				console.warn("[qgis.iface] iface_zoom_to_layer mock");
				return true;
			},
			iface_show_message: () => {
				console.warn("[qgis.iface] iface_show_message mock");
				return true;
			},
			iface_active_layer: () => {
				console.warn("[qgis.iface] iface_active_layer mock");
				return true;
			},
		});
	}

	async zoomToLayer(id: string): Promise<boolean> {
		return this.transport.call("iface_zoom_to_layer", [id]);
	}

	async showMessage(
		title: string,
		message: string,
		level = 0,
		duration = 5,
	): Promise<boolean> {
		return this.transport.call("iface_show_message", [
			title,
			message,
			level,
			duration,
		]);
	}

	async activeLayer(): Promise<any> {
		return this.transport.call("iface_active_layer", []);
	}
}
