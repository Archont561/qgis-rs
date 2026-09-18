/** qgis.message API */

import type { QgisBridge } from '../window';

export class MessageAPI {
  constructor(private _bridge: QgisBridge, private _raw: any) {}

  private async _call(method: string, ...args: any[]): Promise<boolean> {
    if (this._raw && typeof this._raw[method] === 'function') {
      return new Promise((resolve, reject) => {
        try {
          this._raw[method](...args, (res: any) => resolve(!!res));
        } catch (e) {
          reject(e);
        }
      });
    }
    if (this._bridge && typeof (this._bridge as any)[method] === 'function') {
      return (this._bridge as any)[method](...args);
    }
    console.log(`[qgis.message] ${method}:`, ...args);
    return true;
  }

  async info(title: string, message: string, duration = 5): Promise<boolean> {
    return this._call('message_info', title, message, duration);
  }

  async warning(title: string, message: string, duration = 5): Promise<boolean> {
    return this._call('message_warning', title, message, duration);
  }

  async critical(title: string, message: string, duration = 5): Promise<boolean> {
    return this._call('message_critical', title, message, duration);
  }

  async success(title: string, message: string, duration = 5): Promise<boolean> {
    return this._call('message_success', title, message, duration);
  }
}
