/** qgis.layers API for JS */

import type { QgisBridge } from '../window';

export interface QgisLayerInfo {
  id: string;
  name: string;
  type: 'vector' | 'raster' | 'unknown';
  crs?: string;
  featureCount?: number;
}

export class LayersAPI {
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
    // Fallback to bridge.call if method exists there
    if (this._bridge && typeof (this._bridge as any)[method] === 'function') {
      return (this._bridge as any)[method](...args);
    }
    // Mock for testing
    console.warn(`[qgis.layers] ${method} called without QGIS, returning mock`);
    if (method === 'layers_list') return [];
    if (method === 'layers_active') return null;
    return null;
  }

  async list(): Promise<QgisLayerInfo[]> {
    return this._call('layers_list');
  }

  async active(): Promise<QgisLayerInfo | null> {
    return this._call('layers_active');
  }

  async addVector(path: string, name = '', provider = 'ogr'): Promise<QgisLayerInfo> {
    return this._call('layers_add_vector', path, name, provider);
  }

  async addRaster(path: string, name = '', provider = 'gdal'): Promise<QgisLayerInfo> {
    return this._call('layers_add_raster', path, name, provider);
  }

  async remove(id: string): Promise<boolean> {
    return this._call('layers_remove', id);
  }

  async zoomTo(id: string): Promise<boolean> {
    return this._call('layers_zoom_to', id);
  }

  async setActive(id: string): Promise<boolean> {
    return this._call('layers_set_active', id);
  }

  async get(id: string): Promise<QgisLayerInfo | null> {
    return this._call('layers_get', id);
  }

  // Event helpers
  onAdded(cb: (e: CustomEvent) => void): () => void {
    const handler = cb as EventListener;
    this._bridge.addEventListener('layer_added', handler);
    return () => this._bridge.removeEventListener('layer_added', handler);
  }

  onRemoved(cb: (e: CustomEvent) => void): () => void {
    const handler = cb as EventListener;
    this._bridge.addEventListener('layer_removed', handler);
    return () => this._bridge.removeEventListener('layer_removed', handler);
  }
}
