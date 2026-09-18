/** qgis.settings API */

import type { QgisBridge } from '../window';

export class SettingsAPI {
  constructor(private _bridge: QgisBridge, private _raw: any) {}

  private async _call(method: string, ...args: any[]): Promise<any> {
    if (this._raw && typeof this._raw[method] === 'function') {
      return new Promise((resolve, reject) => {
        try {
          this._raw[method](...args, (res: any) => resolve(res));
        } catch (e) {
          reject(e);
        }
      });
    }
    if (this._bridge && typeof (this._bridge as any)[method] === 'function') {
      return (this._bridge as any)[method](...args);
    }
    console.warn(`[qgis.settings] ${method} mock`);
    if (method === 'settings_get') return args[1] || '';
    return true;
  }

  async get(key: string, def = ''): Promise<string> {
    return this._call('settings_get', key, def);
  }

  async set(key: string, value: string): Promise<boolean> {
    return this._call('settings_set', key, value);
  }
}
