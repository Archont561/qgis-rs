/** qgis.processing API */

import type { QgisBridge } from '../window';

export class ProcessingAPI {
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
    console.warn(`[qgis.processing] ${method} mock`);
    return { task_id: 'mock', status: 'queued' };
  }

  async run(algId: string, params: any): Promise<any> {
    return this._call('processing_run', algId, params);
  }
}
