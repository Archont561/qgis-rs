/** qgis.iface API */

import type { QgisBridge } from '../window';

export class IfaceAPI {
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
    console.warn(`[qgis.iface] ${method} mock`);
    return true;
  }

  async zoomToLayer(id: string): Promise<boolean> {
    return this._call('iface_zoom_to_layer', id);
  }

  async showMessage(title: string, message: string, level = 0, duration = 5): Promise<boolean> {
    return this._call('iface_show_message', title, message, level, duration);
  }

  async activeLayer(): Promise<any> {
    return this._call('iface_active_layer');
  }
}
