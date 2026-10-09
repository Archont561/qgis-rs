/** qgis.message API */

import { QgisTransportAdapter } from "@/qgis/transport";
import type { QgisBridge } from "@/window";

interface MessageOperations {
	message_info(title: string, message: string, duration: number): boolean;
	message_warning(title: string, message: string, duration: number): boolean;
	message_critical(title: string, message: string, duration: number): boolean;
	message_success(title: string, message: string, duration: number): boolean;
}

export class MessageAPI {
	private readonly transport: QgisTransportAdapter<MessageOperations>;

	constructor(bridge: QgisBridge, raw: unknown) {
		this.transport = new QgisTransportAdapter(bridge, raw, {
			message_info: (...args) => {
				console.log("[qgis.message] message_info:", ...args);
				return true;
			},
			message_warning: (...args) => {
				console.log("[qgis.message] message_warning:", ...args);
				return true;
			},
			message_critical: (...args) => {
				console.log("[qgis.message] message_critical:", ...args);
				return true;
			},
			message_success: (...args) => {
				console.log("[qgis.message] message_success:", ...args);
				return true;
			},
		});
	}

	async info(title: string, message: string, duration = 5): Promise<boolean> {
		return this.transport.call("message_info", [title, message, duration], {
			callbackResponse: "boolean",
		});
	}

	async warning(
		title: string,
		message: string,
		duration = 5,
	): Promise<boolean> {
		return this.transport.call("message_warning", [title, message, duration], {
			callbackResponse: "boolean",
		});
	}

	async critical(
		title: string,
		message: string,
		duration = 5,
	): Promise<boolean> {
		return this.transport.call("message_critical", [title, message, duration], {
			callbackResponse: "boolean",
		});
	}

	async success(
		title: string,
		message: string,
		duration = 5,
	): Promise<boolean> {
		return this.transport.call("message_success", [title, message, duration], {
			callbackResponse: "boolean",
		});
	}
}
