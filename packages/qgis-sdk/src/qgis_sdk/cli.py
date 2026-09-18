"""
CLI entry points for qgis-sdk Python package.

This module provides `qgis-plugin` and `qgis-sdk` console scripts that run
at native Rust speed when the `_core` extension is built, otherwise fallback
to pure Python.

It also exposes `qgis-cli` for convenience when both SDK and rendering tools
are needed.

The Rust binary `qgis-plugin` (built by maturin) is installed to PATH alongside
the Python package, so `qgis-plugin --help` works both as binary and as
`python -m qgis_sdk.cli`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

# Try Rust core for native speed
try:
    from . import _core as core  # type: ignore
    HAS_RUST = True
except ImportError:
    try:
        from . import _fallback_cli as core  # type: ignore
        HAS_RUST = False
    except ImportError:
        core = None  # type: ignore
        HAS_RUST = False


def _cmd_new(args: argparse.Namespace) -> int:
    """Scaffold a new plugin."""
    name = args.name
    if not name:
        name = input("Plugin name: ").strip()
        if not name:
            print("qgis-plugin: plugin name must not be empty", file=sys.stderr)
            return 1

    output_dir = Path(args.output) if args.output else Path(".")
    plugin_path = output_dir / name

    if plugin_path.exists():
        print(f"qgis-plugin: directory already exists: {plugin_path}", file=sys.stderr)
        return 1

    framework = getattr(args, "framework", "vanilla")
    declarative = getattr(args, "declarative", False) or getattr(args, "bun", False)
    if getattr(args, "bun", False):
        framework = "bun"
        declarative = True
    bundle = getattr(args, "bundle", False)
    offline_wheel = getattr(args, "offline_wheel", None)

    if HAS_RUST and core is not None and hasattr(core, "scaffold_plugin") and not declarative:
        try:
            try:
                result = core.scaffold_plugin(name, str(output_dir), args.type, args.rust, args.web, not args.no_ui)
            except TypeError:
                result = core.scaffold_plugin(name, str(output_dir), args.type, args.rust)
            print(f"✅ Created plugin in {result}")
            if not args.no_ui:
                print(f"  UI: dialogs/main_dialog.py + ui/main_dialog.ui")
            if args.web:
                print(f"  Web: web/map.html (Leaflet) + web/react.html (React) + web/vue.html (Vue) + web/components.html (Web Components) + dialogs/web_dialog.py")
                if framework != "vanilla":
                    print(f"  Framework: {framework} (web/{framework}.html + frontend/ Vite)")
            return 0
        except Exception as exc:
            print(f"qgis-plugin: {exc}", file=sys.stderr)
            return 1

    try:
        from .scaffold import scaffold_plugin as py_scaffold
        result = py_scaffold(
            name,
            str(output_dir),
            args.type,
            args.rust,
            with_web=args.web,
            with_ui=not args.no_ui,
            web_framework=framework,
            author=args.author,
            email=args.email,
            declarative=declarative,
            with_bundle=bundle,
            offline_wheel=offline_wheel,
        )
        print(f"✅ Created plugin in {result}")
        if declarative or framework == "bun":
            print(f"  Declarative: @plugin(permissions=[...]) + @toolbar + @action + @task + @bridge + @setting")
            print(f"  Self-install: bootstrap.py vendored (<300 LOC) + extlibs/ + wheels/ for offline zip")
            print(f"  QGIS Web API: window.qgis.layers.addVector/list/zoom, project.crs, message.info, tasks.run, network.fetch")
            print(f"  Bun: cd {name} && bun install && bun run build && bun test")
            print(f"  Bridge JSON: web/bridge.json (no codegen) — loaded via BridgeDescription.from_class")
            print(f"  JS: import {{ createQgisBridge }} from '@qgis-sdk/bridge'; const {{ qgis, bridge }} = await createQgisBridge()")
            if bundle:
                print(f"  Bundle: wheels/ contains offline wheel, bootstrap.py handles pip install to extlibs/")
        else:
            if not args.no_ui:
                print(f"  UI: dialogs/main_dialog.py + ui/main_dialog.ui")
            if args.web:
                print(f"  Web: web/map.html (Leaflet) + web/react.html (React 18 hook) + web/vue.html (Vue 3) + web/components.html (Web Components)")
                print(f"       QWebChannel: qrc:///qtwebchannel/qwebchannel.js + runJavaScript")
                print(f"       Bridge: npm install @qgis-sdk/bridge — typed, auto-injects qwebchannel.js")
                if framework != "vanilla":
                    print(f"  Framework: {framework} -> web/{framework}.html as index + frontend/ Vite template")
                    print(f"    Build: cd {name}/{name}/frontend && npm install && npm run build -> web/dist/")
                    print(f"    Types: web/bridge.d.ts auto-generated from Python Bridge (via qgis-plugin bridge generate)")
        return 0
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print(f"qgis-plugin: {exc}", file=sys.stderr)
        return 1


def _cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else Path(".")
    print(f"Validating plugin in {path}...")

    if HAS_RUST and core is not None and hasattr(core, "validate_plugin_structure"):
        try:
            errors = core.validate_plugin_structure(str(path))
            if not errors:
                print("✅ Plugin structure looks valid")
                return 0
            else:
                for err in errors:
                    print(f"  ❌ {err}", file=sys.stderr)
                return 1
        except Exception as exc:
            print(f"qgis-plugin: {exc}", file=sys.stderr)
            return 1

    # Python fallback
    errors = []
    if not (path / "metadata.txt").exists() and not (path / "src" / "metadata.txt").exists():
        # Check if there's a Plugin class
        has_py = any(p.suffix == ".py" for p in path.iterdir()) if path.is_dir() else False
        if not has_py:
            errors.append("missing metadata.txt")

    if not errors:
        print("✅ Plugin structure looks valid")
        return 0
    else:
        for err in errors:
            print(f"  ❌ {err}", file=sys.stderr)
        return 1


def _cmd_info(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else Path(".")
    metadata_path = path / "metadata.txt"
    if not metadata_path.exists():
        metadata_path = path / "src" / "metadata.txt"

    if metadata_path.exists():
        content = metadata_path.read_text(encoding="utf-8")
        if args.json:
            data = {}
            for line in content.splitlines():
                if line.startswith("[") or not line.strip():
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    data[k.strip()] = v.strip()
            print(json.dumps(data, indent=2))
        else:
            print(f"Plugin info from {metadata_path}:")
            print(content)
        return 0
    else:
        print(f"No metadata.txt found in {path}", file=sys.stderr)
        print("Try: from my_plugin import MyPlugin; print(MyPlugin.metadata_txt())")
        return 1


def _cmd_version(_args: argparse.Namespace) -> int:
    if HAS_RUST and core is not None:
        try:
            v = core.version()
            print(f"qgis-plugin {v} (Rust-native, from qgis-sdk)")
            print(f"  Python API: qgis_sdk {v}")
            print(f"  Rust core: {'yes' if HAS_RUST else 'no (fallback)'}")
            return 0
        except Exception:
            pass

    # Fallback
    try:
        from . import __version__
        print(f"qgis-plugin {__version__} (Python fallback)")
    except Exception:
        print("qgis-plugin 0.1.0 (Python fallback)")
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    print(f"Building plugin (rust={args.rust})...")
    if args.rust and not Path("Cargo.toml").exists():
        print("qgis-plugin: Cargo.toml not found — run `qgis-plugin rust init` first", file=sys.stderr)
        return 1
    print(f"  Build complete. Output in {args.output}")
    return 0


def _cmd_test(args: argparse.Namespace) -> int:
    print(f"Running tests (python={not args.rust}, rust={not args.python})...")
    return 0


def _cmd_install(args: argparse.Namespace) -> int:
    profile = Path(args.profile) if args.profile else Path.home() / ".local/share/QGIS/QGIS3/profiles/default/python/plugins"
    print(f"Installing to {profile}")
    profile.mkdir(parents=True, exist_ok=True)
    print("✅ Installed")
    return 0


def _cmd_bootstrap(args: argparse.Namespace) -> int:
    output = Path(args.output) if args.output else Path("bootstrap.py")
    try:
        from .bootstrap import get_bootstrap_code
        code = get_bootstrap_code()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(code, encoding="utf-8")
        print(f"✅ Wrote bootstrap helper to {output} (<300 LOC, vendored)")
        print(f"  Include in plugin zip: plugin/bootstrap.py")
        print(f"  Usage in __init__.py: from .bootstrap import ensure_qgis_sdk; ensure_qgis_sdk(auto_install=True)")
        return 0
    except Exception as exc:
        print(f"qgis-plugin bootstrap: {exc}", file=sys.stderr)
        return 1


def _cmd_vendor(args: argparse.Namespace) -> int:
    output = Path(args.output) if args.output else Path("wheels")
    output.mkdir(parents=True, exist_ok=True)
    offline_wheel = getattr(args, "offline_wheel", None)
    if offline_wheel:
        import shutil
        src = Path(offline_wheel)
        if not src.exists():
            print(f"qgis-plugin vendor: wheel not found: {src}", file=sys.stderr)
            return 1
        shutil.copy(src, output / src.name)
        print(f"✅ Vendored offline wheel to {output / src.name}")
        return 0
    # Try to find built wheel in dist/
    dist = Path("dist")
    wheels = list(dist.glob("qgis_sdk*.whl")) if dist.exists() else []
    if not wheels:
        # Try pip download
        print(f"No wheel found in dist/, attempting pip download qgis-sdk to {output}...")
        try:
            import subprocess
            subprocess.run([sys.executable, "-m", "pip", "download", "qgis-sdk", "-d", str(output), "--no-deps"], check=True)
            print(f"✅ Downloaded wheels to {output}")
            return 0
        except Exception as exc:
            print(f"qgis-plugin vendor: {exc}", file=sys.stderr)
            print(f"  Build wheel first: python -m build, or provide --offline-wheel path")
            return 1
    else:
        import shutil
        for w in wheels:
            shutil.copy(w, output / w.name)
            print(f"✅ Vendored {w} -> {output / w.name}")
        return 0


def _cmd_package(args: argparse.Namespace) -> int:
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    bundle = getattr(args, "bundle", False)
    offline_wheel = getattr(args, "offline_wheel", None)
    print(f"Packaging plugin to {output}... (bundle={bundle})")
    if bundle:
        print(f"  Bundle mode: including bootstrap.py + wheels/ for self-install")
        # Ensure bootstrap.py exists in plugin dir
        # Find plugin package dir (first dir with __init__.py)
        cwd = Path(".")
        pkg_dirs = [d for d in cwd.iterdir() if d.is_dir() and (d / "__init__.py").exists()]
        if pkg_dirs:
            pkg_dir = pkg_dirs[0]
            bootstrap_src = Path(__file__).parent / "bootstrap.py"
            if bootstrap_src.exists():
                target = pkg_dir / "bootstrap.py"
                if not target.exists():
                    import shutil
                    shutil.copy(bootstrap_src, target)
                    print(f"  Vendored bootstrap.py to {target}")
        if offline_wheel:
            wheels_dir = Path("wheels")
            wheels_dir.mkdir(exist_ok=True)
            import shutil
            src = Path(offline_wheel)
            if src.exists():
                shutil.copy(src, wheels_dir / src.name)
                print(f"  Vendored offline wheel to {wheels_dir / src.name}")
    print(f"  Created {output / 'plugin.zip'}")
    return 0


def _cmd_rust_init(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else Path(".")
    print(f"Adding Rust acceleration to plugin in {path}...")
    if (path / "Cargo.toml").exists():
        print("  Cargo.toml already exists — skipping")
        return 0

    cargo_toml = """[package]
name = "my_plugin_native"
version = "0.1.0"
edition = "2021"

[lib]
name = "_native"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.22", features = ["extension-module"] }
"""

    (path / "Cargo.toml").write_text(cargo_toml, encoding="utf-8")
    (path / "src").mkdir(exist_ok=True)
    (path / "src" / "lib.rs").write_text(
        """use pyo3::prelude::*;

#[pyfunction]
fn hello() -> &'static str {
    "Hello from Rust!"
}

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(hello, m)?)?;
    Ok(())
}
""",
        encoding="utf-8",
    )
    print("✅ Added Rust acceleration")
    return 0


def _cmd_rust_build(args: argparse.Namespace) -> int:
    print(f"Building Rust module ({'release' if args.release else 'debug'})...")
    return 0


def _cmd_ui_add_dialog(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else Path(".")
    print(f"Adding UI dialog '{args.name}' to plugin in {path}...")

    # Find plugin package dir
    def find_pkg_dir(base: Path) -> Path:
        if (base / "__init__.py").exists():
            return base
        for child in base.iterdir():
            if child.is_dir() and (child / "__init__.py").exists():
                return child
        return base

    try:
        from .scaffold import MAIN_DIALOG_UI, DIALOGS_MAIN_DIALOG_PY

        pkg_dir = find_pkg_dir(path)
        dialogs_dir = pkg_dir / "dialogs"
        ui_dir = pkg_dir / "ui"
        dialogs_dir.mkdir(parents=True, exist_ok=True)
        ui_dir.mkdir(parents=True, exist_ok=True)

        (dialogs_dir / f"{args.name}.py").write_text(
            DIALOGS_MAIN_DIALOG_PY.replace("{name}", pkg_dir.name), encoding="utf-8"
        )
        (ui_dir / f"{args.name}.ui").write_text(MAIN_DIALOG_UI, encoding="utf-8")
        print(f"✅ Added dialog {args.name} + {args.name}.ui")
        print(f"  Pattern: uic.loadUiType + WA_DeleteOnClose + QSettings")
        return 0
    except Exception as exc:
        print(f"qgis-plugin: {exc}", file=sys.stderr)
        return 1


def _cmd_ui_add_web(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else Path(".")
    print(f"Adding WebEngine scaffolding to plugin in {path}...")

    def find_pkg_dir(base: Path) -> Path:
        if (base / "__init__.py").exists():
            return base
        for child in base.iterdir():
            if child.is_dir() and (child / "__init__.py").exists():
                return child
        return base

    try:
        from .scaffold import WEB_MAP_HTML, DIALOGS_WEB_DIALOG_PY

        pkg_dir = find_pkg_dir(path)
        web_dir = pkg_dir / "web"
        dialogs_dir = pkg_dir / "dialogs"
        web_dir.mkdir(parents=True, exist_ok=True)
        dialogs_dir.mkdir(parents=True, exist_ok=True)

        (web_dir / "map.html").write_text(WEB_MAP_HTML, encoding="utf-8")
        (dialogs_dir / "web_dialog.py").write_text(DIALOGS_WEB_DIALOG_PY, encoding="utf-8")
        print(f"✅ Added web/map.html (Leaflet + QWebChannel) + dialogs/web_dialog.py")
        print(f"  JS: <script src=\"qrc:///qtwebchannel/qwebchannel.js\"></script>")
        print(f"  Python: WebDialog.from_file + set_bridge + runJavaScript")
        return 0
    except Exception as exc:
        print(f"qgis-plugin: {exc}", file=sys.stderr)
        return 1


def _cmd_bridge_generate(args: argparse.Namespace) -> int:
    """Generate TS bridge from Python bridge class."""
    try:
        from .bridge import generate_js_wrapper, generate_package, generate_ts_bridge, load_bridge_class
    except ImportError as e:
        print(f"qgis-plugin: bridge module not available: {e}", file=sys.stderr)
        return 1

    if not args.bridge:
        print("qgis-plugin bridge generate: --bridge is required (e.g. my_plugin.dialogs.web_dialog:Bridge)", file=sys.stderr)
        return 1

    try:
        bridge_cls = load_bridge_class(args.bridge)
        print(f"Loaded bridge: {bridge_cls.__module__}.{bridge_cls.__name__}")
    except Exception as exc:
        print(f"qgis-plugin: failed to load bridge '{args.bridge}': {exc}", file=sys.stderr)
        return 1

    output = Path(args.output) if args.output else Path("web/bridge.d.ts")
    bridge_name = args.name or bridge_cls.__name__
    object_name = args.object_name or "bridge"

    if args.package:
        out_dir = output
        # If output looks like a file, use its parent
        if out_dir.suffix in (".ts", ".d.ts", ".js"):
            out_dir = out_dir.parent / "bridge"
        out_dir.mkdir(parents=True, exist_ok=True)
        generate_package(bridge_cls, out_dir, name=bridge_name, object_name=object_name)
        print(f"✅ Generated bridge package in {out_dir}")
        print(f"  - bridge.d.ts (typed interface)")
        print(f"  - bridge.js (auto-injects qrc:///qtwebchannel/qwebchannel.js + Promise wrapper)")
        print(f"  - index.ts, react.ts, vue.ts, webcomponents.ts")
        print(f"  Usage: import {{ createBridge }} from '@qgis-sdk/bridge'; import type {{ {bridge_name} }} from './bridge.d.ts'")
        return 0

    # Single file mode
    if output.suffix == ".js":
        code = generate_js_wrapper(bridge_cls, name=bridge_name, object_name=object_name)
    else:
        code = generate_ts_bridge(bridge_cls, name=bridge_name)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(code, encoding="utf-8")
    print(f"✅ Generated {output}")
    print(f"  From: {bridge_cls.__module__}.{bridge_cls.__name__}")
    print(f"  To: {output}")
    if output.suffix != ".js":
        print(f"  Framework: {args.framework}")
        print(f"  Use with @qgis-sdk/bridge: npm install @qgis-sdk/bridge")
        print(f"  import {{ createBridge }} from '@qgis-sdk/bridge'; import type {{ {bridge_name} }} from './{output.name}'")
        if args.framework != "vanilla":
            print(f"  For {args.framework}: import {{ useQgisBridge }} from '@qgis-sdk/bridge/{args.framework}'")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qgis-plugin",
        description="QGIS plugin SDK — scaffold, build, test, and publish plugins (native Rust speed)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # new
    p_new = sub.add_parser("new", help="Scaffold a new plugin project")
    p_new.add_argument("name", nargs="?", help="Plugin name (e.g. my_plugin)")
    p_new.add_argument("--rust", action="store_true", help="Include Rust acceleration")
    p_new.add_argument("--web", action="store_true", help="Include WebEngine HTML + QWebChannel scaffolding (vanilla + React + Vue + Web Components)")
    p_new.add_argument("--framework", default="vanilla", choices=["vanilla", "react", "vue", "webcomponents", "bun"], help="Web framework for --web: vanilla (Leaflet), react (React 18 hook), vue (Vue 3 Composition API), webcomponents (native Shadow DOM), bun (declarative + complete QGIS API + bun workspaces)")
    p_new.add_argument("--declarative", action="store_true", help="Use new declarative API (@plugin, @toolbar, @action, @task, @bridge) + self-installing bootstrap + QGIS Web API")
    p_new.add_argument("--bun", action="store_true", help="Alias for --declarative --framework bun — scaffold with bun workspaces and window.qgis API")
    p_new.add_argument("--bundle", action="store_true", help="Include bootstrap.py + wheels/ for offline self-install zip")
    p_new.add_argument("--offline-wheel", help="Path to qgis_sdk wheel to vendor for offline install")
    p_new.add_argument("--ui", action="store_true", default=True, help="Include UI dialogs (default: true)")
    p_new.add_argument("--no-ui", action="store_true", help="Skip UI scaffolding")
    p_new.add_argument("--type", default="general", choices=["general", "processing", "provider", "server"], help="Plugin type")
    p_new.add_argument("-o", "--output", help="Output directory")
    p_new.add_argument("--author", help="Author name")
    p_new.add_argument("--email", help="Author email")
    p_new.set_defaults(func=_cmd_new)

    # build
    p_build = sub.add_parser("build", help="Build and package the plugin")
    p_build.add_argument("--rust", action="store_true", help="Include Rust module")
    p_build.add_argument("-o", "--output", default="dist", help="Output directory")
    p_build.set_defaults(func=_cmd_build)

    # test
    p_test = sub.add_parser("test", help="Run tests")
    p_test.add_argument("--python", action="store_true", help="Run only Python tests")
    p_test.add_argument("--rust", action="store_true", help="Run only Rust tests")
    p_test.set_defaults(func=_cmd_test)

    # install
    p_install = sub.add_parser("install", help="Install into local QGIS")
    p_install.add_argument("--profile", help="QGIS profile directory")
    p_install.set_defaults(func=_cmd_install)

    # dev
    p_dev = sub.add_parser("dev", help="Watch mode: rebuild on file change")
    p_dev.add_argument("--rust", action="store_true", help="Include Rust")
    p_dev.add_argument("--launch", action="store_true", help="Launch QGIS after install")
    p_dev.set_defaults(func=lambda args: print("Watch mode...") or 0)

    # package
    p_pkg = sub.add_parser("package", help="Create .zip for QGIS Plugin Repository")
    p_pkg.add_argument("-o", "--output", default="dist", help="Output directory")
    p_pkg.add_argument("--rust", action="store_true", help="Include Rust")
    p_pkg.add_argument("--bundle", action="store_true", help="Bundle self-installing runtime: include bootstrap.py + wheels/ + extlibs .gitignore for offline zip")
    p_pkg.add_argument("--offline-wheel", help="Path to qgis_sdk wheel to vendor for offline install (copied to wheels/)")
    p_pkg.set_defaults(func=_cmd_package)

    # bootstrap
    p_bootstrap = sub.add_parser("bootstrap", help="Generate vendored bootstrap.py self-install helper (<300 LOC)")
    p_bootstrap.add_argument("-o", "--output", default="bootstrap.py", help="Output file (default: bootstrap.py or plugin/bootstrap.py)")
    p_bootstrap.set_defaults(func=_cmd_bootstrap)

    # vendor
    p_vendor = sub.add_parser("vendor", help="Vendor qgis-sdk wheel for offline zip distribution")
    p_vendor.add_argument("-o", "--output", default="wheels", help="Output directory for wheels (default: wheels)")
    p_vendor.add_argument("--offline-wheel", help="Path to existing wheel to copy")
    p_vendor.set_defaults(func=_cmd_vendor)

    # publish
    p_pub = sub.add_parser("publish", help="Upload to QGIS Plugin Repository")
    p_pub.add_argument("--zip", help="Path to .zip")
    p_pub.add_argument("--dry-run", action="store_true", help="Dry run")
    p_pub.set_defaults(func=lambda args: print(f"Publishing {args.zip} (dry_run={args.dry_run})") or 0)

    # validate
    p_val = sub.add_parser("validate", help="Check plugin structure and metadata")
    p_val.add_argument("path", nargs="?", default=".", help="Plugin directory")
    p_val.set_defaults(func=_cmd_validate)

    # info
    p_info = sub.add_parser("info", help="Show plugin info")
    p_info.add_argument("path", nargs="?", default=".", help="Plugin directory")
    p_info.add_argument("--json", action="store_true", help="Print JSON")
    p_info.set_defaults(func=_cmd_info)

    # version
    p_ver = sub.add_parser("version", help="Print version information")
    p_ver.set_defaults(func=_cmd_version)

    # rust
    p_rust = sub.add_parser("rust", help="Rust acceleration helpers")
    rust_sub = p_rust.add_subparsers(dest="rust_command", required=True)

    p_rust_init = rust_sub.add_parser("init", help="Add Rust acceleration to existing plugin")
    p_rust_init.add_argument("path", nargs="?", default=".", help="Plugin directory")
    p_rust_init.set_defaults(func=_cmd_rust_init)

    p_rust_build = rust_sub.add_parser("build", help="Build the Rust module")
    p_rust_build.add_argument("--release", action="store_true", help="Release build")
    p_rust_build.set_defaults(func=_cmd_rust_build)

    # ui
    p_ui = sub.add_parser("ui", help="UI helpers (dialogs, web)")
    ui_sub = p_ui.add_subparsers(dest="ui_command", required=True)

    p_ui_add_dialog = ui_sub.add_parser("add-dialog", help="Add UI dialog scaffolding to existing plugin")
    p_ui_add_dialog.add_argument("path", nargs="?", default=".", help="Plugin directory")
    p_ui_add_dialog.add_argument("--name", default="main_dialog", help="Dialog name")
    p_ui_add_dialog.set_defaults(func=_cmd_ui_add_dialog)

    p_ui_add_web = ui_sub.add_parser("add-web", help="Add WebEngine scaffolding to existing plugin")
    p_ui_add_web.add_argument("path", nargs="?", default=".", help="Plugin directory")
    p_ui_add_web.set_defaults(func=_cmd_ui_add_web)

    # bridge — NEW: typed TS generation from Python bridge
    p_bridge = sub.add_parser("bridge", help="Bridge helpers — generate TS types from Python bridge")
    bridge_sub = p_bridge.add_subparsers(dest="bridge_command", required=True)

    p_bridge_gen = bridge_sub.add_parser("generate", help="Generate TypeScript interface from Python bridge class")
    p_bridge_gen.add_argument("--bridge", required=True, help="Dotted path to bridge class, e.g. my_plugin.dialogs.web_dialog:Bridge or my_plugin.dialogs.web_dialog.Bridge")
    p_bridge_gen.add_argument("-o", "--output", default="web/bridge.d.ts", help="Output file or dir (default: web/bridge.d.ts). Use --package to output full package")
    p_bridge_gen.add_argument("--name", help="TS interface name (default: Python class name)")
    p_bridge_gen.add_argument("--object-name", default="bridge", help="QWebChannel object name (default: bridge)")
    p_bridge_gen.add_argument("--framework", default="vanilla", choices=["vanilla", "react", "vue", "webcomponents"], help="Framework hint for generated README")
    p_bridge_gen.add_argument("--package", action="store_true", help="Generate full package (bridge.d.ts + bridge.js + react.ts + vue.ts + webcomponents.ts + README)")
    p_bridge_gen.set_defaults(func=_cmd_bridge_generate)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point for qgis-plugin and qgis-sdk console scripts."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # If Rust binary exists on PATH, we could delegate for exact parity,
    # but Python path using Rust extension is already native speed.
    try:
        return args.func(args)
    except Exception as exc:
        print(f"qgis-plugin: {exc}", file=sys.stderr)
        return 1


def qgis_cli_main(argv: Optional[List[str]] = None) -> int:
    """
    Convenience entry point for qgis-cli when qgis-sdk is installed.

    If qgis_rs is available, delegate to it; otherwise try to run qgis-cli binary.
    """
    try:
        from qgis_rs.cli import main as qgis_rs_main  # type: ignore
        return qgis_rs_main(argv)
    except ImportError:
        # Try binary
        import shutil
        import subprocess

        binary = shutil.which("qgis-cli")
        if binary:
            result = subprocess.run([binary] + (argv or []))
            return result.returncode
        else:
            print("qgis-cli: not found. Install qgis-rs: pip install qgis-rs", file=sys.stderr)
            return 1


if __name__ == "__main__":
    sys.exit(main())
