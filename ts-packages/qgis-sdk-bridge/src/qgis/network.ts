/** qgis.network API — via QGIS NAM */

import type { QgisBridge } from '../window';

export interface QgisNetworkResponse {
  ok: boolean;
  status: number;
  headers: Record<string, string>;
  url: string;
  body?: string;
  error?: string;
  text(): Promise<string>;
  json(): Promise<any>;
}

export class NetworkAPI {
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
    // Fallback to browser fetch if not in QGIS (for testing)
    console.warn(`[qgis.network] ${method} fallback to browser fetch`);
    const url = args[0];
    try {
      const resp = await fetch(url);
      const text = await resp.text();
      return {
        status: resp.status,
        headers: Object.fromEntries(resp.headers.entries()),
        body: text,
        ok: resp.ok,
        url,
      };
    } catch (e) {
      return { status: 0, headers: {}, body: '', ok: false, error: String(e), url };
    }
  }

  async fetch(url: string, opts: { method?: string; headers?: any; body?: string; authCfg?: string } = {}): Promise<QgisNetworkResponse> {
    const res = await this._call('network_fetch', url, opts.method || 'GET', opts.headers || {}, opts.body || null, opts.authCfg || null);
    
    return {
      ok: res.ok,
      status: res.status,
      headers: res.headers || {},
      url: res.url || url,
      body: res.body,
      error: res.error,
      text: async () => res.body || '',
      json: async () => {
        try {
          return JSON.parse(res.body || '{}');
        } catch {
          return null;
        }
      }
    };
  }

  async get(url: string, opts: { headers?: any; authCfg?: string } = {}): Promise<QgisNetworkResponse> {
    return this.fetch(url, { method: 'GET', ...opts });
  }

  async post(url: string, body?: string, opts: { headers?: any; authCfg?: string } = {}): Promise<QgisNetworkResponse> {
    return this.fetch(url, { method: 'POST', body, ...opts });
  }
}
