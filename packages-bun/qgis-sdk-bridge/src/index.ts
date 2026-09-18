/**
 * @qgis-sdk/bridge — Typed QWebChannel bridge for QGIS plugins, with complete QGIS Web API
 * 
 * New architecture:
 * - Description loader: loads BridgeDescription JSON from Python (no codegen needed)
 * - Window-like: QgisBridge extends EventTarget, readyState, onopen/onmessage/send/close
 * - Complete QGIS API: window.qgis with layers, project, message, tasks, network, iface, settings, processing
 * 
 * Built with bun — bun install, bun test, bun build
 * 
 * @example Vanilla JS with complete QGIS API
 * ```typescript
 * import { createQgisBridge } from '@qgis-sdk/bridge';
 * const { bridge, qgis } = await createQgisBridge();
 * 
 * await qgis.message.info("Hello", "From JS");
 * const layer = await qgis.layers.addVector("/path/to.shp", "Roads");
 * const task = await qgis.tasks.run("buffer_task", {distance: 10});
 * const resp = await qgis.network.fetch("https://example.com/api");
 * ```
 * 
 * @example Custom bridge still works
 * ```typescript
 * import { createBridge } from '@qgis-sdk/bridge';
 * const bridge = await createBridge();
 * const data = await bridge.get_layer("my_layer");
 * ```
 */

export { QgisBridge, createBridge } from './window.js';
export type { BridgeOptions } from './window.js';

export { QgisAPI, createQgisBridge, getQgis, qgis } from './qgis.js';
export type { QgisBridgeResult, QgisLayerInfo, QgisProjectInfo, QgisTaskHandle, QgisNetworkResponse } from './qgis.js';

export { loadDescription, loadQgisApiDescription, loadBridgeName, loadQgisApiName, createBridgeFromDescription, descriptionToTypeScript } from './description.js';
export type { BridgeDescription, MethodDescription } from './description.js';

export { loadQWebChannel, isQWebChannelAvailable, QWEBCHANNEL_SOURCES } from './loader.js';

// For backwards compat
export { createQgisBridge as createQGISBridge } from './qgis.js';

// Default export is createQgisBridge for new API, but also provide createBridge
import { createQgisBridge } from './qgis.js';
import { createBridge } from './window.js';

export default createQgisBridge;
export { createBridge as createTypedBridge };

// Re-export sub-APIs for direct import
export { LayersAPI } from './qgis/layers.js';
export { ProjectAPI } from './qgis/project.js';
export { MessageAPI } from './qgis/message.js';
export { TasksAPI } from './qgis/tasks.js';
export { NetworkAPI } from './qgis/network.js';
export { IfaceAPI } from './qgis/iface.js';
export { SettingsAPI } from './qgis/settings.js';
export { ProcessingAPI } from './qgis/processing.js';

// Python → JS helpers
export type QgisMessageHandler = (data: any) => void;

const messageHandlers = new Set<QgisMessageHandler>();

export function onQgisMessage(handler: QgisMessageHandler): () => void {
  messageHandlers.add(handler);
  return () => messageHandlers.delete(handler);
}

function setupGlobalHandlers() {
  if (typeof window === 'undefined') return;

  const w = window as any;
  w.qgisBridge = w.qgisBridge || {};
  
  // Will be overwritten by createBridge/createQgisBridge
  w.qgisBridge.onMessage = (data: any) => {
    messageHandlers.forEach(h => {
      try { h(data); } catch (e) { console.error('[qgis-bridge] handler error', e); }
    });
    window.dispatchEvent(new CustomEvent('qgis-message', { detail: data }));
    window.dispatchEvent(new CustomEvent('qgis-bridge-message', { detail: data }));
  };

  w.updateFromPython = w.updateFromPython || w.qgisBridge.onMessage;
  w.updateFromReact = w.updateFromReact || w.qgisBridge.onMessage;
  w.updateFromVue = w.updateFromVue || w.qgisBridge.onMessage;
  w.updateFromWC = w.updateFromWC || w.qgisBridge.onMessage;
}

if (typeof window !== 'undefined') {
  setupGlobalHandlers();
}
