/** qgis-sdk-bridge qgis.ts — high-level QGIS API for JS, built with bun */

import { QgisBridge } from './window';
import { loadQgisApiDescription } from './description';

// Sub-APIs
import { LayersAPI, type QgisLayerInfo } from './qgis/layers';
import { ProjectAPI, type QgisProjectInfo } from './qgis/project';
import { MessageAPI } from './qgis/message';
import { TasksAPI, type QgisTaskHandle } from './qgis/tasks';
import { NetworkAPI, type QgisNetworkResponse } from './qgis/network';
import { IfaceAPI } from './qgis/iface';
import { SettingsAPI } from './qgis/settings';
import { ProcessingAPI } from './qgis/processing';

export type { QgisLayerInfo, QgisProjectInfo, QgisTaskHandle, QgisNetworkResponse };

export class QgisAPI extends EventTarget {
  // Sub-APIs
  layers: LayersAPI;
  project: ProjectAPI;
  message: MessageAPI;
  messageBar: { pushMessage: (title: string, text: string, level?: number, duration?: number) => Promise<boolean> };
  tasks: TasksAPI;
  network: NetworkAPI;
  iface: IfaceAPI;
  settings: SettingsAPI;
  processing: ProcessingAPI;

  private _bridge: QgisBridge;
  private _raw: any;

  constructor(bridge: QgisBridge, rawQgis: any) {
    super();
    this._bridge = bridge;
    this._raw = rawQgis;

    this.layers = new LayersAPI(bridge, rawQgis);
    this.project = new ProjectAPI(bridge, rawQgis);
    this.message = new MessageAPI(bridge, rawQgis);
    this.messageBar = {
      pushMessage: (title: string, text: string, level = 0, duration = 5) => this.message.info(title, text, duration)
    };
    this.tasks = new TasksAPI(bridge, rawQgis);
    this.network = new NetworkAPI(bridge, rawQgis);
    this.iface = new IfaceAPI(bridge, rawQgis);
    this.settings = new SettingsAPI(bridge, rawQgis);
    this.processing = new ProcessingAPI(bridge, rawQgis);

    // Wire bridge signals to this EventTarget
    this._wireSignals();
  }

  private _wireSignals() {
    // Listen to bridge events and re-dispatch as qgis events
    const signals = ['layer_added', 'layer_removed', 'task_progress', 'task_finished', 'message'];
    signals.forEach(sig => {
      this._bridge.addEventListener(sig, (e: any) => {
        this.dispatchEvent(new CustomEvent(sig, { detail: e.detail || e.data }));
      });
    });
  }

  get raw() {
    return this._raw;
  }

  get bridge() {
    return this._bridge;
  }
}

// Global singleton, like window.qgis
export let qgis: QgisAPI;

export function getQgis(): QgisAPI | null {
  return qgis || (typeof window !== 'undefined' ? (window as any).qgis : null) || null;
}

export interface QgisBridgeResult<T = any> {
  bridge: T & QgisBridge;
  qgis: QgisAPI;
}

export async function createQgisBridge<T = QgisBridge>(
  objectName: string | import('./window').BridgeOptions = 'bridge',
  options: import('./window').BridgeOptions = {}
): Promise<QgisBridgeResult<T>> {
  const { createBridge } = await import('./window.js');
  
  const opts = typeof objectName === 'string' ? { objectName, ...options } : objectName;
  const bridgeName = (opts as any).objectName || (typeof objectName === 'string' ? objectName : 'bridge');
  
  const bridge = await createBridge<T>(bridgeName, opts) as T & QgisBridge;
  
  // Get raw qgis object
  const rawQgis = await (bridge as any)._getRawQgis();
  
  // If no raw qgis but description available, create mock for testing
  let qgisApi: QgisAPI;
  if (rawQgis) {
    qgisApi = new QgisAPI(bridge, rawQgis);
  } else {
    // Create mock that still works for description-based testing
    const qgisDesc = loadQgisApiDescription();
    if (qgisDesc) {
      console.log('[qgis-sdk] QGIS API description found, but no raw qgis object — creating mock');
    }
    // Create mock raw that uses bridge.call for qgis methods if available, or mock
    const mockRaw: any = {};
    // If bridge has qgis methods directly (unlikely), use them
    qgisApi = new QgisAPI(bridge, mockRaw);
  }
  
  qgis = qgisApi;
  
  if (typeof window !== 'undefined') {
    (window as any).qgis = qgisApi;
    (window as any).qgisBridge = bridge;
  }
  
  // Wire signals from Python to JS EventTarget via bridge
  bridge.addEventListener('layer_added', (e: any) => qgisApi.dispatchEvent(new CustomEvent('layer_added', { detail: e.detail })));
  bridge.addEventListener('layer_removed', (e: any) => qgisApi.dispatchEvent(new CustomEvent('layer_removed', { detail: e.detail })));
  bridge.addEventListener('task_progress', (e: any) => qgisApi.dispatchEvent(new CustomEvent('task_progress', { detail: e.detail })));
  bridge.addEventListener('task_finished', (e: any) => qgisApi.dispatchEvent(new CustomEvent('task_finished', { detail: e.detail })));
  
  return { bridge, qgis: qgisApi };
}

// For backwards compat
export const createQGISBridge = createQgisBridge;
