import { describe, it, expect, beforeEach } from "bun:test";
import { QgisBridge } from "../src/window.ts";
import { loadDescription, loadQgisApiDescription } from "../src/description.ts";
import { QgisAPI } from "../src/qgis.ts";
import { LayersAPI } from "../src/qgis/layers.ts";
import { TasksAPI } from "../src/qgis/tasks.ts";
import { NetworkAPI } from "../src/qgis/network.ts";
import { MessageAPI } from "../src/qgis/message.ts";

// Mock QWebChannel for testing without QGIS
(globalThis as any).QWebChannel = class {
  constructor(transport: any, cb: any) {
    const makeCb = (args: any[], result: any) => {
      const last = args[args.length - 1];
      if (typeof last === 'function') last(result);
    };
    // Simulate channel with mock objects
    const mockBridge = {
      get_layer: (...args: any[]) => makeCb(args, JSON.stringify({ name: args[0], count: 42 })),
      log: (...args: any[]) => makeCb(args, "ok"),
      layers_list: (...args: any[]) => makeCb(args, JSON.stringify([{ id: "layer1", name: "Roads", type: "vector" }])),
      layers_add_vector: (...args: any[]) => {
        const [path, name] = args;
        makeCb(args, JSON.stringify({ id: "layer_new", name: name || "Roads", type: "vector", path }));
      },
      tasks_run: (...args: any[]) => makeCb(args, JSON.stringify({ task_id: "task123", name: args[0] })),
      message_info: (...args: any[]) => makeCb(args, true),
      network_fetch: (...args: any[]) => makeCb(args, JSON.stringify({ ok: true, status: 200, url: args[0], body: JSON.stringify({ mock: true }), headers: {} })),
    };
    const mockQgis = {
      layers_list: (...args: any[]) => makeCb(args, JSON.stringify([{ id: "layer1", name: "Roads" }])),
      layers_add_vector: (...args: any[]) => {
        const [path, name] = args;
        makeCb(args, JSON.stringify({ id: "layer_new", name: name || "Roads", type: "vector" }));
      },
      tasks_run: (...args: any[]) => makeCb(args, JSON.stringify({ task_id: "task123", name: args[0] })),
      message_info: (...args: any[]) => makeCb(args, true),
      network_fetch: (...args: any[]) => makeCb(args, JSON.stringify({ ok: true, status: 200, url: args[0], body: JSON.stringify({ mock: true }), headers: {} })),
    };
    const channel = {
      objects: {
        bridge: mockBridge,
        my_bridge: mockBridge,
        qgis: mockQgis,
      }
    };
    cb(channel);
  }
};

(globalThis as any).qt = {
  webChannelTransport: {}
};

(globalThis as any).window = globalThis;
(globalThis as any).__QGIS_BRIDGE_DESCRIPTION__ = {
  name: "my_bridge",
  version: "0.1.0",
  methods: [
    { name: "get_layer", args: ["layer_id"], arg_types: ["string"], return_type: "object" },
    { name: "log", args: ["msg"], arg_types: ["string"], return_type: "string" }
  ],
  signals: [
    { name: "layer_changed", args: ["layer_id"], arg_types: ["string"] }
  ]
};

(globalThis as any).__QGIS_API_DESCRIPTION__ = {
  name: "qgis",
  version: "0.1.0",
  methods: [
    { name: "layers_list", args: [], arg_types: [], return_type: "object" },
    { name: "layers_add_vector", args: ["path", "name", "provider"], arg_types: ["string", "string", "string"], return_type: "object" },
    { name: "tasks_run", args: ["name", "params"], arg_types: ["string", "object"], return_type: "object" },
    { name: "message_info", args: ["title", "text", "duration"], arg_types: ["string", "string", "number"], return_type: "boolean" },
    { name: "network_fetch", args: ["url", "options"], arg_types: ["string", "object"], return_type: "object" },
  ],
  signals: []
};

describe("QgisBridge - EventTarget/WebSocket-like", () => {
  it("should have WebSocket readyState constants", () => {
    expect(QgisBridge.CONNECTING).toBe(0);
    expect(QgisBridge.OPEN).toBe(1);
    expect(QgisBridge.CLOSING).toBe(2);
    expect(QgisBridge.CLOSED).toBe(3);
  });

  it("should create bridge and open", async () => {
    const { createBridge } = await import("../src/window.ts");
    const bridge = await createBridge("my_bridge");
    expect(bridge.readyState).toBe(QgisBridge.OPEN);
    expect(bridge.objectName).toBe("my_bridge");
  });

  it("should call method via Promise", async () => {
    const { createBridge } = await import("../src/window.ts");
    const bridge = await createBridge("my_bridge");
    const layer = await (bridge as any).get_layer("test_layer");
    expect(layer.name).toBe("test_layer");
    expect(layer.count).toBe(42);
  });

  it("should support EventTarget addEventListener", async () => {
    const { createBridge } = await import("../src/window.ts");
    const bridge = await createBridge("my_bridge");
    let called = false;
    bridge.addEventListener("layer_changed", () => { called = true; });
    bridge.dispatchEvent(new CustomEvent("layer_changed", { detail: { layer_id: "layer1" } }));
    expect(called).toBe(true);
  });

  it("should support onopen/onmessage", async () => {
    const bridge = new QgisBridge("my_bridge");
    let openCalled = false;
    bridge.onopen = () => { openCalled = true; };
    await bridge._connect();
    expect(openCalled).toBe(true);
    expect(bridge.readyState).toBe(QgisBridge.OPEN);
  });

  it("should load description JSON not codegen", async () => {
    const desc = loadDescription();
    expect(desc).not.toBeNull();
    expect(desc!.name).toBe("my_bridge");
    expect(desc!.methods.length).toBe(2);
  });
});

describe("QgisAPI - complete QGIS Web API", () => {
  it("should load QGIS API description", () => {
    const desc = loadQgisApiDescription();
    expect(desc).not.toBeNull();
    expect(desc!.methods.find(m => m.name === "layers_list")).toBeDefined();
  });

  it("should create QgisAPI with sub-APIs", async () => {
    const { createQgisBridge } = await import("../src/qgis.ts");
    const { qgis, bridge } = await createQgisBridge("my_bridge");
    expect(qgis).toBeDefined();
    expect(qgis.layers).toBeDefined();
    expect(qgis.project).toBeDefined();
    expect(qgis.message).toBeDefined();
    expect(qgis.tasks).toBeDefined();
    expect(qgis.network).toBeDefined();
    expect(qgis.iface).toBeDefined();
    expect(qgis.settings).toBeDefined();
    expect(qgis.processing).toBeDefined();
  });

  it("should list layers via qgis.layers", async () => {
    const { createQgisBridge } = await import("../src/qgis.ts");
    const { qgis } = await createQgisBridge("my_bridge");
    const layers = await qgis.layers.list();
    expect(Array.isArray(layers)).toBe(true);
    expect(layers[0].name).toBe("Roads");
  });

  it("should add vector layer via qgis.layers.addVector", async () => {
    const { createQgisBridge } = await import("../src/qgis.ts");
    const { qgis } = await createQgisBridge("my_bridge");
    const layer = await qgis.layers.addVector("/data/roads.shp", "Roads");
    expect(layer.name).toBe("Roads");
    expect(layer.id).toBeDefined();
  });

  it("should run task via qgis.tasks.run", async () => {
    const { createQgisBridge } = await import("../src/qgis.ts");
    const { qgis, bridge } = await createQgisBridge("my_bridge");
    const task = await qgis.tasks.run("buffer_task", { distance: 10 });
    expect(task.task_id).toBe("task123");
    let progressCalled = false;
    task.onProgress(() => { progressCalled = true; });
    // Simulate progress event from Python
    bridge.dispatchEvent(new CustomEvent("task_progress", { detail: { task_id: "task123", progress: 50 } }));
    expect(progressCalled).toBe(true);
  });

  it("should show message via qgis.message.info", async () => {
    const { createQgisBridge } = await import("../src/qgis.ts");
    const { qgis } = await createQgisBridge("my_bridge");
    const ok = await qgis.message.info("Title", "Hello from JS", 5);
    expect(ok).toBe(true);
  });

  it("should fetch via qgis.network.fetch (QGIS NAM, no CORS)", async () => {
    const { createQgisBridge } = await import("../src/qgis.ts");
    const { qgis } = await createQgisBridge("my_bridge");
    const resp = await qgis.network.fetch("https://example.com/api");
    expect(resp.ok).toBe(true);
  });

  it("should support window.qgis global", async () => {
    const { createQgisBridge } = await import("../src/qgis.ts");
    await createQgisBridge("my_bridge");
    expect((globalThis as any).qgis).toBeDefined();
    expect((globalThis as any).qgis.layers).toBeDefined();
  });

  it("should support EventTarget for qgis", async () => {
    const { createQgisBridge } = await import("../src/qgis.ts");
    const { qgis, bridge } = await createQgisBridge("my_bridge");
    let called = false;
    qgis.addEventListener("layer_added", () => { called = true; });
    bridge.dispatchEvent(new CustomEvent("layer_added", { detail: { id: "layer1" } }));
    // QgisAPI wires bridge signals to qgis, so dispatching on bridge should trigger qgis listener
    expect(called).toBe(true);
    let qgisCalled = false;
    qgis.addEventListener("custom_event", () => { qgisCalled = true; });
    qgis.dispatchEvent(new CustomEvent("custom_event"));
    expect(qgisCalled).toBe(true);
  });
});

describe("Description loader - no codegen", () => {
  it("should load from window.__QGIS_BRIDGE_DESCRIPTION__", () => {
    const desc = loadDescription();
    expect(desc?.name).toBe("my_bridge");
  });

  it("should create bridge from description", async () => {
    const { createBridgeFromDescription } = await import("../src/description.ts");
    const desc = loadDescription()!;
    const raw = {
      get_layer: (id: string, cb: any) => cb({ name: id }),
      log: (msg: string, cb: any) => cb("ok")
    };
    const bridge = createBridgeFromDescription(desc, raw);
    expect(bridge).toBeDefined();
    expect(typeof (bridge as any).get_layer).toBe("function");
  });
});
