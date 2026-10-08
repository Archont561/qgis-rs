/** qgis.tasks API */

import type { QgisBridge } from "../window";
import { QgisTransportAdapter } from "./transport";

export interface QgisTaskHandle {
	task_id: string;
	status: string;
	name?: string;
	onProgress(cb: (progress: number) => void): () => void;
	onFinished(cb: (result: any) => void): () => void;
	cancel(): Promise<boolean>;
}

interface TaskRunResponse {
	task_id?: string;
	id?: string;
	status?: string;
}

interface TasksOperations {
	tasks_run(name: string, params: unknown): TaskRunResponse;
	tasks_list(): any[];
	tasks_cancel(taskId: string): boolean;
}

const jsonCallback = { callbackResponse: "json" } as const;

export class TasksAPI {
	private readonly transport: QgisTransportAdapter<TasksOperations>;

	constructor(
		private _bridge: QgisBridge,
		raw: unknown,
	) {
		this.transport = new QgisTransportAdapter(_bridge, raw, {
			tasks_run: () => {
				console.warn("[qgis.tasks] tasks_run mock");
				return { task_id: "mock", status: "queued" };
			},
			tasks_list: () => {
				console.warn("[qgis.tasks] tasks_list mock");
				return [];
			},
			tasks_cancel: () => {
				console.warn("[qgis.tasks] tasks_cancel mock");
				return true;
			},
		});
	}

	async run(name: string, params?: any): Promise<QgisTaskHandle> {
		const res = await this.transport.call(
			"tasks_run",
			[name, params || {}],
			jsonCallback,
		);
		const taskId = res.task_id || res.id || "unknown";

		const handle: QgisTaskHandle = {
			task_id: taskId,
			status: res.status || "queued",
			name,
			onProgress: (cb: (progress: number) => void) => {
				const handler = (e: any) => {
					const detail = e.detail || {};
					if (detail.task_id === taskId || detail.id === taskId) {
						cb(detail.progress || 0);
					}
				};
				this._bridge.addEventListener(
					"task_progress",
					handler as EventListener,
				);
				return () =>
					this._bridge.removeEventListener(
						"task_progress",
						handler as EventListener,
					);
			},
			onFinished: (cb: (result: any) => void) => {
				const handler = (e: any) => {
					const detail = e.detail || {};
					if (detail.task_id === taskId || detail.id === taskId) {
						cb(detail.result || detail);
					}
				};
				this._bridge.addEventListener(
					"task_finished",
					handler as EventListener,
				);
				return () =>
					this._bridge.removeEventListener(
						"task_finished",
						handler as EventListener,
					);
			},
			cancel: async () => {
				return this.transport.call("tasks_cancel", [taskId], jsonCallback);
			},
		};

		return handle;
	}

	async list(): Promise<any[]> {
		return this.transport.call("tasks_list", [], jsonCallback);
	}

	async cancel(id: string): Promise<boolean> {
		return this.transport.call("tasks_cancel", [id], jsonCallback);
	}
}
