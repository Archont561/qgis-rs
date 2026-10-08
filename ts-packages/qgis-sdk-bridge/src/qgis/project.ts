/** qgis.project API */

import type { QgisBridge } from "../window";
import { QgisTransportAdapter } from "./transport";

export interface QgisProjectInfo {
	path: string;
	crs: string;
	title: string;
}

interface ProjectOperations {
	project_info(): QgisProjectInfo;
	project_write(): boolean;
	project_crs(): string;
	project_set_crs(authid: string): boolean;
	project_path(): string;
}

const jsonCallback = { callbackResponse: "json" } as const;

export class ProjectAPI {
	private readonly transport: QgisTransportAdapter<ProjectOperations>;

	constructor(bridge: QgisBridge, raw: unknown) {
		this.transport = new QgisTransportAdapter(bridge, raw, {
			project_info: () => {
				console.warn("[qgis.project] project_info mock");
				return { path: "", crs: "", title: "" };
			},
			project_write: () => {
				console.warn("[qgis.project] project_write mock");
				return true;
			},
			project_crs: () => {
				console.warn("[qgis.project] project_crs mock");
				return "";
			},
			project_set_crs: () => {
				console.warn("[qgis.project] project_set_crs mock");
				return true;
			},
			project_path: () => {
				console.warn("[qgis.project] project_path mock");
				return "";
			},
		});
	}

	async info(): Promise<QgisProjectInfo> {
		return this.transport.call("project_info", [], jsonCallback);
	}

	async write(): Promise<boolean> {
		return this.transport.call("project_write", [], jsonCallback);
	}

	async crs(): Promise<string> {
		return this.transport.call("project_crs", [], jsonCallback);
	}

	async setCrs(authid: string): Promise<boolean> {
		return this.transport.call("project_set_crs", [authid], jsonCallback);
	}

	async path(): Promise<string> {
		return this.transport.call("project_path", [], jsonCallback);
	}
}
