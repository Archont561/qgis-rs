//! End-to-end test of the bundled MCP server.
//!
//! This spawns the real `qgis-cli mcp` binary and speaks the Model Context
//! Protocol to it over stdio, exactly like an MCP client would: `initialize`,
//! `notifications/initialized`, `tools/list`, `tools/call`.

#![cfg(feature = "mcp")]

use std::io::{BufRead, BufReader, Write};
use std::process::{Child, Command, Stdio};
use std::sync::mpsc;
use std::time::Duration;

const BINARY: &str = env!("CARGO_BIN_EXE_qgis-cli");

/// A running `qgis-cli mcp`, with its stdio attached.
struct Session {
    stdin: std::process::ChildStdin,
    responses: std::io::Lines<BufReader<std::process::ChildStdout>>,
    _watchdog: mpsc::Sender<()>,
}

impl Session {
    fn start() -> Self {
        let mut child: Child = Command::new(BINARY)
            .arg("mcp")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            // Diagnostics must never reach stdout: the protocol owns it.
            .stderr(Stdio::null())
            .spawn()
            .expect("spawn `qgis-cli mcp`");

        let stdin = child.stdin.take().expect("child stdin");
        let stdout = child.stdout.take().expect("child stdout");

        // If the handshake wedges, kill the child rather than hang CI.
        let (watchdog, finished) = mpsc::channel::<()>();
        std::thread::spawn(move || {
            let mut child = child;
            if finished.recv_timeout(Duration::from_secs(120)).is_err() {
                let _ = child.kill();
            }
            let _ = child.wait();
        });

        Self {
            stdin,
            responses: BufReader::new(stdout).lines(),
            _watchdog: watchdog,
        }
    }

    fn send(&mut self, message: &str) {
        writeln!(self.stdin, "{message}").expect("write to the server");
        self.stdin.flush().expect("flush");
    }

    /// Read until a response for `id` arrives, skipping notifications.
    fn response_for(&mut self, id: u32) -> String {
        let marker = format!("\"id\":{id}");
        for _ in 0..32 {
            let line = self
                .responses
                .next()
                .expect("the server closed stdout")
                .expect("read a response line");
            if line.contains(&marker) {
                return line;
            }
        }
        panic!("no response with {marker}");
    }
}

#[test]
fn handshake_lists_and_calls_the_tools() {
    let mut session = Session::start();

    session.send(
        r#"{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"qgis-rs-test","version":"0.1.0"}}}"#,
    );
    let initialized = session.response_for(1);
    assert!(initialized.contains(r#""result""#), "{initialized}");
    assert!(initialized.contains("qgis-cli"), "{initialized}");
    assert!(initialized.contains("protocolVersion"), "{initialized}");

    session.send(r#"{"jsonrpc":"2.0","method":"notifications/initialized"}"#);

    session.send(r#"{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}"#);
    let tools = session.response_for(2);
    for tool in [
        "capabilities",
        "crs_info",
        "plan_tiles",
        "project_info",
        "render_map",
        "export_features",
    ] {
        assert!(tools.contains(tool), "{tool} missing from: {tools}");
    }
    // The generated input schemas are advertised alongside each tool.
    assert!(tools.contains("inputSchema"), "{tools}");

    session.send(
        r#"{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"crs_info","arguments":{"auth_id":"EPSG:3857"}}}"#,
    );
    let crs = session.response_for(3);
    assert!(crs.contains("Pseudo-Mercator"), "{crs}");
    assert!(crs.contains("meters"), "{crs}");

    session.send(
        r#"{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"plan_tiles","arguments":{"bounds":"14,50,15,51","zoom":"10-14"}}}"#,
    );
    let plan = session.response_for(4);
    assert!(plan.contains("4568"), "{plan}");

    session.send(
        r#"{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"project_info","arguments":{"project":"/definitely/not/here.qgs"}}}"#,
    );
    let missing = session.response_for(5);
    assert!(missing.contains("error"), "{missing}");
    assert!(missing.contains("not found"), "{missing}");

    // Closing stdin ends the session cleanly.
    drop(session.stdin);
}

#[test]
fn a_bad_tool_name_is_rejected() {
    let mut session = Session::start();
    session.send(
        r#"{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"qgis-rs-test","version":"0.1.0"}}}"#,
    );
    session.response_for(1);
    session.send(r#"{"jsonrpc":"2.0","method":"notifications/initialized"}"#);

    session.send(
        r#"{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"not_a_tool","arguments":{}}}"#,
    );
    let response = session.response_for(2);
    assert!(response.contains("error"), "{response}");
    drop(session.stdin);
}

#[test]
fn list_tools_flag_prints_the_catalogue() {
    let output = Command::new(BINARY)
        .args(["mcp", "--list-tools"])
        .output()
        .expect("run `qgis-cli mcp --list-tools`");
    assert!(output.status.success(), "{output:?}");

    let stdout = String::from_utf8_lossy(&output.stdout);
    for tool in ["capabilities", "crs_info", "plan_tiles", "render_map"] {
        assert!(stdout.contains(tool), "{tool} missing from: {stdout}");
    }
    assert!(stdout.contains("[needs QGIS]"), "{stdout}");
}
