/** qgis.project API */

import type { QgisBridge } from '../window';

export interface QgisProjectInfo {
  path: string;
  crs: string;
  title: string;
}

export class ProjectAPI {
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
    console.warn(`[qgis.project] ${method} mock`);
    if (method === 'project_info') return { path: '', crs: '', title: '' };
    if (method === 'project_crs') return '';
    if (method === 'project_path') return '';
    return true;
  }

  async info(): Promise<QgisProjectInfo> {
    return this._call('project_info');
  }

  async write(): Promise<boolean> {
    return this._call('project_write');
  }

  async crs(): Promise<string> {
    return this._call('project_crs');
  }

  async setCrs(authid: string): Promise<boolean> {
    return this._call('project_set_crs', authid);
  }

  async path(): Promise<string> {
    return this._call('project_path');
  }
}
