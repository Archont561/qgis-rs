"""Property tests for pure-Python SDK fakes and value seams."""

from __future__ import annotations

from hypothesis import given, settings, strategies as st


@settings(max_examples=30, deadline=None)
@given(count=st.integers(min_value=0, max_value=50))
def test_mock_source_has_the_requested_feature_count(count: int) -> None:
    from qgis_sdk.testing import mock_source

    source = mock_source(feature_count=count)

    assert source.feature_count == count
    assert len(list(source.features())) == count


@settings(max_examples=30, deadline=None)
@given(progress=st.lists(st.floats(min_value=0, max_value=1), max_size=10))
def test_fake_context_records_bounded_progress(progress: list[float]) -> None:
    from qgis_sdk.testing import FakeContext

    context = FakeContext()
    for value in progress:
        context.set_progress(value)

    assert context.progress == progress
