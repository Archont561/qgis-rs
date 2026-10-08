/** qgis.processing API */

import { QgisTransportAdapter } from "@/ts-packages/qgis-sdk-bridge/src/qgis/transport";
import type { QgisBridge } from "@/ts-packages/qgis-sdk-bridge/src/window";

interface ProcessingOperations {
	processing_run(algorithmId: string, params: unknown): unknown;
}

export class ProcessingAPI {
	private readonly transport: QgisTransportAdapter<ProcessingOperations>;

	constructor(bridge: QgisBridge, raw: unknown) {
		this.transport = new QgisTransportAdapter(bridge, raw, {
			processing_run: () => {
				console.warn("[qgis.processing] processing_run mock");
				return { task_id: "mock", status: "queued" };
			},
		});
	}

	async run(algId: string, params: any): Promise<any> {
		return this.transport.call("processing_run", [algId, params], {
			callbackResponse: "json",
		});
	}
}
