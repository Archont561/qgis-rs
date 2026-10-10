"""
CLI entry points for the qgis-sdk Python package.

`qgis-sdk` runs pure Python. Every command is implemented here or in the
package modules it calls; no native extension is involved.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import zipfile
from enum import Enum
from pathlib import Path
from typing import List, Optional

import typer

from .plugin_validation import validate_plugin_structure


def _cmd_new(args: argparse.Namespace) -> int:
    """Scaffold a new plugin."""
    name = (args.name or "").strip()
    if not name:
        print("qgis-sdk new: a plugin name is required", file=sys.stderr)
        return 2

    output_dir = Path(args.output) if args.output else Path(".")
    plugin_path = output_dir / name

    if plugin_path.exists():
        print(f"qgis-sdk: directory already exists: {plugin_path}", file=sys.stderr)
        return 1

    framework = getattr(args, "framework", "vanilla")
    declarative = getattr(args, "declarative", False) or getattr(args, "bun", False)
    if getattr(args, "bun", False):
        framework = "bun"
        declarative = True
    bundle = getattr(args, "bundle", False)
    offline_wheel = getattr(args, "offline_wheel", None)

    try:
        from .scaffold import scaffold_plugin as py_scaffold
        result = py_scaffold(
            name,
            str(output_dir),
            args.type,
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
            print(f"  JS: import {{ createQgisBridge }} from '@archont561/qgis-sdk'; const {{ qgis, bridge }} = await createQgisBridge()")
            if bundle:
                print(f"  Bundle: wheels/ contains offline wheel, bootstrap.py handles pip install to extlibs/")
        else:
            if not args.no_ui:
                print(f"  UI: dialogs/main_dialog.py + ui/main_dialog.ui")
            if args.web:
                print(f"  Web: web/map.html (Leaflet) + web/react.html (React 18 hook) + web/vue.html (Vue 3) + web/components.html (Web Components)")
                print(f"       QWebChannel: qrc:///qtwebchannel/qwebchannel.js + runJavaScript")
                print(f"       Bridge: npm install @archont561/qgis-sdk — typed, auto-injects qwebchannel.js")
                if framework != "vanilla":
                    print(f"  Framework: {framework} -> web/{framework}.html as index + frontend/ Vite template")
                    print(f"    Build: cd {name}/{name}/frontend && npm install && npm run build -> web/dist/")
                    print(f"    Types: web/bridge.d.ts auto-generated from Python Bridge (via qgis-sdk bridge generate)")
        return 0
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print(f"qgis-sdk: {exc}", file=sys.stderr)
        return 1


def _cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else Path(".")
    print(f"Validating plugin in {path}...")

    try:
        errors, notes = validate_plugin_structure(str(path))
    except ValueError as exc:
        print(f"qgis-sdk: {exc}", file=sys.stderr)
        return 1

    if errors:
        for err in errors:
            print(f"  ❌ {err}", file=sys.stderr)
        print(f"qgis-sdk: validation failed with {len(errors)} errors", file=sys.stderr)
        return 1

    print("✅ Plugin structure looks valid")
    for note in notes:
        print(f"  {note}")
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else Path(".")
    metadata_path = path / "metadata.txt"
    if not metadata_path.exists():
        metadata_path = path / "src" / "metadata.txt"

    if not metadata_path.exists():
        # Matches the retired Rust command: a missing file is information, not an error.
        print(f"No metadata.txt found in {path}")
        print("This might be a qgis-sdk Plugin class — import it to see metadata:")
        print("  from my_plugin import MyPlugin")
        print("  print(MyPlugin.metadata_txt())")
        return 0

    content = metadata_path.read_text(encoding="utf-8")
    if args.json:
        data: dict = {}
        for line in content.splitlines():
            if line.startswith("[") or not line.strip():
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                data[k.strip()] = v.strip()
        # serde_json's default map is sorted; keep that order and raw UTF-8.
        print(json.dumps(dict(sorted(data.items())), indent=2, ensure_ascii=False))
    else:
        print(f"Plugin info from {metadata_path}:")
        print(content)
    return 0


def _cmd_version(_args: argparse.Namespace) -> int:
    from . import __version__

    print(f"qgis-sdk {__version__} (Python, from qgis-sdk)")
    print(
        "  UI: dialogs (.ui + uic.loadUiType) + WebEngine "
        "(QWebChannel, qrc:///qtwebchannel/qwebchannel.js)"
    )
    return 0


def _cmd_test(args: argparse.Namespace) -> int:
    print("Running tests...")
    return subprocess.run([sys.executable, "-m", "pytest", "-q"]).returncode


def _cmd_install(args: argparse.Namespace) -> int:
    profile = Path(args.profile) if args.profile else Path.home() / ".local/share/QGIS/QGIS3/profiles/default/python/plugins"
    try:
        package_dir = _plugin_package_dir(Path("."))
    except ValueError as exc:
        print(f"qgis-sdk install: {exc}", file=sys.stderr)
        return 1
    if package_dir is None:
        print("qgis-sdk install: no plugin package found (a folder with __init__.py)", file=sys.stderr)
        return 1
    target = profile / package_dir.name
    print(f"Installing {package_dir.name} to {target}")
    profile.mkdir(parents=True, exist_ok=True)
    shutil.copytree(package_dir, target, dirs_exist_ok=True, ignore=_ignored_entries)
    metadata = Path(".") / "metadata.txt"
    if metadata.is_file() and not (target / "metadata.txt").exists():
        shutil.copy(metadata, target / "metadata.txt")
    print("✅ Installed")
    return 0


def _cmd_dev(args: argparse.Namespace) -> int:
    print(
        "qgis-sdk dev: watch mode is not implemented in this package. "
        "Run `qgis-sdk build` and `qgis-sdk install` after each change.",
        file=sys.stderr,
    )
    return 2


def _cmd_publish(args: argparse.Namespace) -> int:
    if not args.zip:
        print("qgis-sdk publish: --zip is required", file=sys.stderr)
        return 1
    archive = Path(args.zip)
    if not archive.is_file():
        print(f"qgis-sdk publish: archive not found: {archive}", file=sys.stderr)
        return 1
    if args.dry_run:
        print(f"Dry run: would upload {archive} to the QGIS plugin repository")
        return 0
    print(
        "qgis-sdk publish: upload to the QGIS plugin repository is not implemented. "
        "Use --dry-run to check the archive.",
        file=sys.stderr,
    )
    return 2


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
        print(f"qgis-sdk bootstrap: {exc}", file=sys.stderr)
        return 1


def _cmd_vendor(args: argparse.Namespace) -> int:
    output = Path(args.output) if args.output else Path("wheels")
    output.mkdir(parents=True, exist_ok=True)
    offline_wheel = getattr(args, "offline_wheel", None)
    if offline_wheel:
        import shutil
        src = Path(offline_wheel)
        if not src.exists():
            print(f"qgis-sdk vendor: wheel not found: {src}", file=sys.stderr)
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
            print(f"qgis-sdk vendor: {exc}", file=sys.stderr)
            print(f"  Build wheel first: python -m build, or provide --offline-wheel path")
            return 1
    else:
        import shutil
        for w in wheels:
            shutil.copy(w, output / w.name)
            print(f"✅ Vendored {w} -> {output / w.name}")
        return 0


_IGNORED_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache"}


def _ignored_entries(directory: str, names: List[str]) -> List[str]:
    return [name for name in names if name in _IGNORED_NAMES or name.endswith(".pyc")]


_NOT_PLUGIN_PACKAGES = {"tests", "test", "docs", "dist", "wheels", "build", "node_modules", "extlibs"}


def _plugin_package_dir(base: Path) -> Optional[Path]:
    """The plugin package under ``base``: a child folder with an ``__init__.py``.

    A scaffolded plugin also has a ``tests/`` package, so test, output and hidden folders
    are skipped, and a package named after the project folder wins over any other.
    """
    candidates = sorted(
        child
        for child in base.iterdir()
        if child.is_dir()
        and not child.name.startswith(".")
        and child.name not in _NOT_PLUGIN_PACKAGES
        and (child / "__init__.py").is_file()
    )
    for child in candidates:
        if child.name == base.resolve().name:
            return child
    return candidates[0] if candidates else None


def _archive_plugin(base: Path, output: Path) -> Path:
    """Zip the plugin package under ``output`` as ``<name>.zip`` with a ``<name>/`` root folder."""
    package_dir = _plugin_package_dir(base)
    if package_dir is None:
        raise ValueError("no plugin package found (a folder with __init__.py)")
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"{package_dir.name}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(package_dir.rglob("*")):
            if path.is_dir():
                continue
            relative = path.relative_to(package_dir)
            if any(part in _IGNORED_NAMES for part in relative.parts) or path.suffix == ".pyc":
                continue
            zf.write(path, f"{package_dir.name}/{relative.as_posix()}")
        metadata = base / "metadata.txt"
        if metadata.is_file() and not (package_dir / "metadata.txt").is_file():
            zf.write(metadata, f"{package_dir.name}/metadata.txt")
    return archive


def _vendor_bundle(package_dir: Path, bundle: bool, offline_wheel: Optional[str]) -> None:
    """Copy bootstrap.py and an optional offline wheel into the plugin package."""
    if bundle:
        bootstrap_src = Path(__file__).parent / "bootstrap.py"
        target = package_dir / "bootstrap.py"
        if bootstrap_src.exists() and not target.exists():
            shutil.copy(bootstrap_src, target)
    if offline_wheel:
        wheel = Path(offline_wheel)
        if not wheel.is_file():
            raise ValueError(f"offline wheel not found: {wheel}")
        wheels = package_dir / "wheels"
        wheels.mkdir(exist_ok=True)
        shutil.copy(wheel, wheels / wheel.name)


def _cmd_package(args: argparse.Namespace) -> int:
    bundle = bool(getattr(args, "bundle", False))
    offline_wheel = getattr(args, "offline_wheel", None)
    try:
        package_dir = _plugin_package_dir(Path("."))
        if package_dir is None:
            raise ValueError("no plugin package found (a folder with __init__.py)")
        if bundle or offline_wheel:
            _vendor_bundle(package_dir, bundle, offline_wheel)
        archive = _archive_plugin(Path("."), Path(args.output))
    except ValueError as exc:
        print(f"qgis-sdk package: {exc}", file=sys.stderr)
        return 1
    print(f"✅ Packaged plugin to {archive}")
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    return _cmd_package(args)


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
        print(f"qgis-sdk: {exc}", file=sys.stderr)
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
        print(f"qgis-sdk: {exc}", file=sys.stderr)
        return 1


def _cmd_bridge_generate(args: argparse.Namespace) -> int:
    """Generate TS bridge from Python bridge class."""
    try:
        from .bridge import generate_js_wrapper, generate_package, generate_ts_bridge, load_bridge_class
    except ImportError as e:
        print(f"qgis-sdk: bridge module not available: {e}", file=sys.stderr)
        return 1

    if not args.bridge:
        print("qgis-sdk bridge generate: --bridge is required (e.g. my_plugin.dialogs.web_dialog:Bridge)", file=sys.stderr)
        return 1

    try:
        bridge_cls = load_bridge_class(args.bridge)
        print(f"Loaded bridge: {bridge_cls.__module__}.{bridge_cls.__name__}")
    except Exception as exc:
        print(f"qgis-sdk: failed to load bridge '{args.bridge}': {exc}", file=sys.stderr)
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
        print(f"  Usage: import {{ createBridge }} from '@archont561/qgis-sdk'; import type {{ {bridge_name} }} from './bridge.d.ts'")
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
        print(f"  Use with @archont561/qgis-sdk: npm install @archont561/qgis-sdk")
        print(f"  import {{ createBridge }} from '@archont561/qgis-sdk'; import type {{ {bridge_name} }} from './{output.name}'")
        if args.framework != "vanilla":
            print(f"  For {args.framework}: import {{ useQgisBridge }} from '@archont561/qgis-sdk/{args.framework}'")
    return 0


def _invoke(handler, **kwargs) -> None:
    """Run an ``_cmd_*`` handler with the options typer parsed.

    A non-zero handler result becomes the process exit code.
    """
    code = handler(argparse.Namespace(**kwargs))
    if code:
        raise typer.Exit(code)


def _ask_dialog_name() -> str:
    """Ask for a dialog name only at an interactive terminal; otherwise use the default."""
    default = "main_dialog"
    if not _interactive():
        return default
    import questionary

    answer = questionary.text("Dialog name", default=default).ask()
    if answer is None:
        raise typer.Abort()
    return answer.strip() or default


app = typer.Typer(
    name="qgis-sdk",
    help="QGIS plugin SDK: scaffold, build, test, install, and package QGIS plugins.",
    no_args_is_help=True,
    add_completion=False,
)
ui_app = typer.Typer(help="Add UI scaffolding to a plugin.", no_args_is_help=True)
bridge_app = typer.Typer(help="Generate bridge typings for web UIs.", no_args_is_help=True)
app.add_typer(ui_app, name="ui")
app.add_typer(bridge_app, name="bridge")

class PluginType(str, Enum):
    general = "general"
    processing = "processing"
    provider = "provider"
    server = "server"


class Framework(str, Enum):
    vanilla = "vanilla"
    react = "react"
    vue = "vue"
    webcomponents = "webcomponents"
    bun = "bun"


class BridgeFramework(str, Enum):
    vanilla = "vanilla"
    react = "react"
    vue = "vue"
    webcomponents = "webcomponents"


def _interactive() -> bool:
    """True only at a terminal, where a prompt can be answered. A CI run never prompts."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def _answered(answer):
    """questionary returns None on Ctrl-C; that aborts the command like any typer prompt."""
    if answer is None:
        raise typer.Abort()
    return answer


@app.command("new")
def new_command(
    name: Optional[str] = typer.Argument(None, help="Plugin name, for example my_plugin. Asked for at a terminal when omitted."),
    plugin_type: Optional[PluginType] = typer.Option(None, "--type", help="Plugin type. Asked for at a terminal when omitted (default: general)."),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Directory to create the plugin in."),
    web: bool = typer.Option(False, "--web", help="Include a web UI."),
    framework: Framework = typer.Option(Framework.vanilla, "--framework", help="Web UI framework."),
    declarative: bool = typer.Option(False, "--declarative", help="Use the declarative plugin layout."),
    bun: bool = typer.Option(False, "--bun", help="Use Bun for the web UI (implies --declarative)."),
    bundle: bool = typer.Option(False, "--bundle", help="Include bootstrap.py and wheels/ for an offline self-install zip."),
    offline_wheel: Optional[str] = typer.Option(None, "--offline-wheel", help="Path to a qgis_sdk wheel to vendor for offline install."),
    ui: Optional[bool] = typer.Option(None, "--ui/--no-ui", help="Include UI dialogs. Asked for at a terminal when omitted (default: yes)."),
    author: Optional[str] = typer.Option(None, "--author", help="Plugin author. Asked for at a terminal when omitted."),
    email: Optional[str] = typer.Option(None, "--email", help="Author email. Asked for at a terminal when omitted."),
) -> int:
    """Scaffold a new plugin."""
    interactive = _interactive()
    if not name:
        if not interactive:
            print("qgis-sdk new: a plugin name is required when not running at a terminal", file=sys.stderr)
            raise typer.Exit(2)
        import questionary

        name = _answered(questionary.text("Plugin name", default="my_plugin").ask())
    if plugin_type is None:
        if interactive:
            import questionary

            choice = _answered(
                questionary.select(
                    "Plugin type",
                    choices=[item.value for item in PluginType],
                    default=PluginType.general.value,
                ).ask()
            )
            plugin_type = PluginType(choice)
        else:
            plugin_type = PluginType.general
    if ui is None:
        if interactive:
            import questionary

            ui = _answered(questionary.confirm("Include UI dialogs?", default=True).ask())
        else:
            ui = True
    if interactive and author is None:
        import questionary

        author = _answered(questionary.text("Author", default="").ask()).strip() or None
    if interactive and email is None:
        import questionary

        email = _answered(questionary.text("Author email", default="").ask()).strip() or None
    return _invoke(
        _cmd_new,
        name=name,
        type=plugin_type.value,
        output=output,
        web=web,
        framework=framework.value,
        declarative=declarative,
        bun=bun,
        bundle=bundle,
        offline_wheel=offline_wheel,
        no_ui=not ui,
        author=author,
        email=email,
    )


@app.command("validate")
def validate_command(path: str = typer.Argument(".", help="Plugin directory.")) -> int:
    """Check a plugin's structure and metadata."""
    return _invoke(_cmd_validate, path=path)


@app.command("info")
def info_command(
    path: str = typer.Argument(".", help="Plugin directory."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> int:
    """Show plugin information."""
    return _invoke(_cmd_info, path=path, json=json_output)


@app.command("version")
def version_command() -> int:
    """Print the qgis-sdk version."""
    return _invoke(_cmd_version)


@app.command("build")
def build_command(
    output: str = typer.Option("dist", "-o", "--output", help="Directory for the plugin archive."),
) -> int:
    """Build and package the plugin."""
    return _invoke(_cmd_build, output=output)


@app.command("package")
def package_command(
    output: str = typer.Option("dist", "-o", "--output", help="Directory for the plugin archive."),
    bundle: bool = typer.Option(False, "--bundle", help="Include bootstrap.py and wheels/ for an offline self-install zip."),
    offline_wheel: Optional[str] = typer.Option(None, "--offline-wheel", help="Path to a qgis_sdk wheel to vendor for offline install."),
) -> int:
    """Zip the plugin package into an archive QGIS can install."""
    return _invoke(_cmd_package, output=output, bundle=bundle, offline_wheel=offline_wheel)


@app.command("test")
def test_command() -> int:
    """Run the plugin's Python tests with pytest."""
    return _invoke(_cmd_test)


@app.command("install")
def install_command(
    profile: Optional[str] = typer.Option(None, "--profile", help="QGIS plugins directory (default: the default profile)."),
) -> int:
    """Copy the plugin into a QGIS profile."""
    return _invoke(_cmd_install, profile=profile)


@app.command("dev")
def dev_command(
    launch: bool = typer.Option(False, "--launch", help="Launch QGIS after install."),
) -> int:
    """Watch mode: rebuild on file change (not implemented)."""
    return _invoke(_cmd_dev, launch=launch)


@app.command("publish")
def publish_command(
    zip_path: Optional[str] = typer.Option(None, "--zip", help="Archive to publish."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Check the archive without uploading."),
) -> int:
    """Upload an archive to the QGIS plugin repository (not implemented; use --dry-run)."""
    return _invoke(_cmd_publish, zip=zip_path, dry_run=dry_run)


@app.command("bootstrap")
def bootstrap_command(
    output: str = typer.Option("bootstrap.py", "-o", "--output", help="Where to write bootstrap.py."),
) -> int:
    """Write the bootstrap.py helper."""
    return _invoke(_cmd_bootstrap, output=output)


@app.command("vendor")
def vendor_command(
    output: str = typer.Option("wheels", "-o", "--output", help="Directory for vendored wheels."),
    offline_wheel: Optional[str] = typer.Option(None, "--offline-wheel", help="Wheel to vendor."),
) -> int:
    """Vendor wheels for offline installs."""
    return _invoke(_cmd_vendor, output=output, offline_wheel=offline_wheel)


@ui_app.command("add-dialog")
def ui_add_dialog_command(
    path: Optional[str] = typer.Argument(None, help="Plugin directory."),
    name: Optional[str] = typer.Option(None, "--name", help="Dialog name (default: main_dialog)."),
) -> int:
    """Add a dialog to a plugin. Asks for the name at a terminal."""
    if name is None:
        name = _ask_dialog_name()
    return _invoke(_cmd_ui_add_dialog, path=path, name=name)


@ui_app.command("add-web")
def ui_add_web_command(path: Optional[str] = typer.Argument(None, help="Plugin directory.")) -> int:
    """Add a web UI to a plugin."""
    return _invoke(_cmd_ui_add_web, path=path)


@bridge_app.command("generate")
def bridge_generate_command(
    bridge: str = typer.Option(..., "--bridge", help="Dotted path to bridge class, e.g. my_plugin.dialogs.web_dialog:Bridge."),
    output: str = typer.Option("web/bridge.d.ts", "-o", "--output", help="Output file or dir (default: web/bridge.d.ts)."),
    name: Optional[str] = typer.Option(None, "--name", help="TS interface name (default: Python class name)."),
    object_name: str = typer.Option("bridge", "--object-name", help="QWebChannel object name (default: bridge)."),
    framework: BridgeFramework = typer.Option(BridgeFramework.vanilla, "--framework", help="Framework hint for generated README."),
    package: bool = typer.Option(False, "--package", help="Generate the full package (bridge.d.ts, bridge.js, framework wrappers, README)."),
) -> int:
    """Generate TypeScript typings for a bridge."""
    return _invoke(
        _cmd_bridge_generate,
        bridge=bridge,
        output=output,
        name=name,
        object_name=object_name,
        framework=framework.value,
        package=package,
    )


def main(argv: Optional[List[str]] = None) -> int:
    """Run the CLI and return the exit code. Usage errors return 2."""
    command = typer.main.get_command(app)
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        command.main(args=args, prog_name="qgis-sdk")
    except SystemExit as exc:
        return int(exc.code or 0)
    except Exception as exc:  # pragma: no cover - defensive, keeps the exit code honest
        print(f"qgis-sdk: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
