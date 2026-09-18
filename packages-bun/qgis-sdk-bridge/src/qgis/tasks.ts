/** qgis.tasks API */

import type { QgisBridge } from '../window';

export interface QgisTaskHandle {
  task_id: string;
  status: string;
  name?: string;
  onProgress(cb: (progress: number) => void): () => void;
  onFinished(cb: (result: any) => void): () => void;
  cancel(): Promise<boolean>;
}

export class TasksAPI {
  constructor(private _bridge: QgisBridge, private _raw: any) {}

  private async _call(method: string, ...args: any[]): Promise<any> {
    if (this._raw && typeof this._raw[method] === 'function') {
      return new Promise((resolve, reject) => {
        try {
          this._raw[method](...args, (res: any) => {
            if (typeof res === 'string') {
              try {
                const parsed = JSON.parse(res);
                resolve(parsed);
                return;
              } catch {}
            }
            resolve(res);
          });
        } catch (e) {
          reject(e);
        }
      });
    }
    if (this._bridge && typeof (this._bridge as any)[method] === 'function') {
      return (this._bridge as any)[method](...args);
    }
    console.warn(`[qgis.tasks] ${method} mock`);
    if (method === 'tasks_list') return [];
    if (method === 'tasks_run') return { task_id: 'mock', status: 'queued' };
    return true;
  }

  async run(name: string, params?: any): Promise<QgisTaskHandle> {
    const res = await this._call('tasks_run', name, params || {});
    const taskId = res.task_id || res.id || 'unknown';

    const handle: QgisTaskHandle = {
      task_id: taskId,
      status: res.status || 'queued',
      name,
      onProgress: (cb: (progress: number) => void) => {
        const handler = (e: any) => {
          const detail = e.detail || {};
          if (detail.task_id === taskId || detail.id === taskId) {
            cb(detail.progress || 0);
          }
        };
        this._bridge.addEventListener('task_progress', handler as EventListener);
        return () => this._bridge.removeEventListener('task_progress', handler as EventListener);
      },
      onFinished: (cb: (result: any) => void) => {
        const handler = (e: any) => {
          const detail = e.detail || {};
          if (detail.task_id === taskId || detail.id === taskId) {
            cb(detail.result || detail);
          }
        };
        this._bridge.addEventListener('task_finished', handler as EventListener);
        return () => this._bridge.removeEventListener('task_finished', handler as EventListener);
      },
      cancel: async () => {
        return this._call('tasks_cancel', taskId);
      }
    };

    return handle;
  }

  async list(): Promise<any[]> {
    return this._call('tasks_list');
  }

  async cancel(id: string): Promise<boolean> {
    return this._call('tasks_cancel', id);
  }
}
