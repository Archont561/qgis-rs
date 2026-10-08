/** qgis.layers API for JS */

import { QgisTransportAdapter } from "@/qgis/transport";
import type { QgisBridge } from "@/window";

export interface QgisLayerInfo {
	id: string;
	name: string;
	type: "vector" | "raster" | "unknown";
	crs?: string;
	featureCount?: number;
}

interface LayersOperations {
	layers_list(): QgisLayerInfo[];
	layers_active(): QgisLayerInfo | null;
	layers_add_vector(
		path: string,
		name: string,
		provider: string,
	): QgisLayerInfo | null;
	layers_add_raster(
		path: string,
		name: string,
		provider: string,
	): QgisLayerInfo | null;
	layers_remove(id: string): boolean | null;
	layers_zoom_to(id: string): boolean | null;
	layers_set_active(id: string): boolean | null;
	layers_get(id: string): QgisLayerInfo | null;
}

const jsonCallback = { callbackResponse: "json" } as const;

export class LayersAPI {
	private readonly transport: QgisTransportAdapter<LayersOperations>;

	constructor(
		private _bridge: QgisBridge,
		raw: unknown,
	) {
		this.transport = new QgisTransportAdapter(_bridge, raw, {
			layers_list: () => {
				console.warn(
					"[qgis.layers] layers_list called without QGIS, returning mock",
				);
				return [];
			},
			layers_active: () => {
				console.warn(
					"[qgis.layers] layers_active called without QGIS, returning mock",
				);
				return null;
			},
			layers_add_vector: () => {
				console.warn(
					"[qgis.layers] layers_add_vector called without QGIS, returning mock",
				);
				return null;
			},
			layers_add_raster: () => {
				console.warn(
					"[qgis.layers] layers_add_raster called without QGIS, returning mock",
				);
				return null;
			},
			layers_remove: () => {
				console.warn(
					"[qgis.layers] layers_remove called without QGIS, returning mock",
				);
				return null;
			},
			layers_zoom_to: () => {
				console.warn(
					"[qgis.layers] layers_zoom_to called without QGIS, returning mock",
				);
				return null;
			},
			layers_set_active: () => {
				console.warn(
					"[qgis.layers] layers_set_active called without QGIS, returning mock",
				);
				return null;
			},
			layers_get: () => {
				console.warn(
					"[qgis.layers] layers_get called without QGIS, returning mock",
				);
				return null;
			},
		});
	}

	async list(): Promise<QgisLayerInfo[]> {
		return this.transport.call("layers_list", [], jsonCallback);
	}

	async active(): Promise<QgisLayerInfo | null> {
		return this.transport.call("layers_active", [], jsonCallback);
	}

	async addVector(
		path: string,
		name = "",
		provider = "ogr",
	): Promise<QgisLayerInfo> {
		return (await this.transport.call(
			"layers_add_vector",
			[path, name, provider],
			jsonCallback,
		)) as QgisLayerInfo;
	}

	async addRaster(
		path: string,
		name = "",
		provider = "gdal",
	): Promise<QgisLayerInfo> {
		return (await this.transport.call(
			"layers_add_raster",
			[path, name, provider],
			jsonCallback,
		)) as QgisLayerInfo;
	}

	async remove(id: string): Promise<boolean> {
		return (await this.transport.call(
			"layers_remove",
			[id],
			jsonCallback,
		)) as boolean;
	}

	async zoomTo(id: string): Promise<boolean> {
		return (await this.transport.call(
			"layers_zoom_to",
			[id],
			jsonCallback,
		)) as boolean;
	}

	async setActive(id: string): Promise<boolean> {
		return (await this.transport.call(
			"layers_set_active",
			[id],
			jsonCallback,
		)) as boolean;
	}

	async get(id: string): Promise<QgisLayerInfo | null> {
		return this.transport.call("layers_get", [id], jsonCallback);
	}

	// Event helpers
	onAdded(cb: (e: CustomEvent) => void): () => void {
		const handler = cb as EventListener;
		this._bridge.addEventListener("layer_added", handler);
		return () => this._bridge.removeEventListener("layer_added", handler);
	}

	onRemoved(cb: (e: CustomEvent) => void): () => void {
		const handler = cb as EventListener;
		this._bridge.addEventListener("layer_removed", handler);
		return () => this._bridge.removeEventListener("layer_removed", handler);
	}
}
