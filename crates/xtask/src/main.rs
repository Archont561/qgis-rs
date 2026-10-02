//! The `xtask` entry point: parse, dispatch, done.
//!
//! Everything this binary can do lives in the library next door
//! (`src/lib.rs`), because the tests in `tests/` are a consumer of it and an
//! integration test cannot reach a binary target. Keeping `main` this thin is
//! the point: there is no behaviour here that a test could miss.

use anyhow::Result;
use clap::Parser;
use xtask::Cli;

fn main() -> Result<()> {
    xtask::run(Cli::parse().command)
}
