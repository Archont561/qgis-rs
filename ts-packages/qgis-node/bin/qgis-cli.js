#!/usr/bin/env node
/* qgis-cli — the binary shipped in the platform package for this machine. */

process.exitCode = require("../src/cli.js").main();
