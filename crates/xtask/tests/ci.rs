//! The gate's two pure helpers: the log tail, and the filter that decides
//! which lines of a failed run name a cause worth putting in the summary.

use xtask::ci::{last, INTERESTING};

#[test]
fn the_tail_helper_keeps_order_and_bounds() {
    let lines = ["one", "two", "three"];
    assert_eq!(last(&lines, 2), ["two", "three"]);
    assert_eq!(last(&lines, 9), ["one", "two", "three"]);
    assert!(last(&[], 5).is_empty());
}

#[test]
fn the_interesting_filter_finds_causes_not_passes() {
    let log = "test foo ... ok\nerror: cannot find value\nrunning 3 tests\nFAILED bar\n";
    let found: Vec<&str> = log
        .lines()
        .filter(|line| INTERESTING.iter().any(|needle| line.contains(needle)))
        .collect();
    assert_eq!(found, ["error: cannot find value", "FAILED bar"]);
}
