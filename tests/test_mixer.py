from hypothesis import given
from hypothesis import strategies as st

from core.mixer import build_lavfi_complex
from core.types import MixSelection


@st.composite
def mix_selections(draw: st.DrawFn) -> list[MixSelection]:
    """Strategy to generate a list of MixSelections representing a file's tracks."""
    size = draw(st.integers(min_value=0, max_value=8))
    selections = []
    for i in range(1, size + 1):
        # Allow a reasonable range for volume, matching typical UI bounds
        vol = draw(st.floats(min_value=0.0, max_value=2.0))
        enabled = draw(st.booleans())
        selections.append(MixSelection(index=i, volume=vol, enabled=enabled))
    return selections


@given(mix_selections())
def test_build_lavfi_complex_properties(selections: list[MixSelection]) -> None:
    """Property-based tests ensuring invariants of the lavfi graph builder."""
    result = build_lavfi_complex(selections)

    enabled_count = sum(1 for s in selections if s.enabled)

    # Invariant 1: If no tracks are enabled, return the silent source
    if enabled_count == 0:
        assert result == "anullsrc[ao]"
        return

    # Invariant 2: A valid mix must always end with the final output node [ao]
    assert result.endswith("[ao]")

    # Invariant 3: Multiple inputs must be joined by amix
    if enabled_count > 1:
        expected_amix = f"amix=inputs={enabled_count}:duration=longest[ao]"
        assert expected_amix in result

    # Invariant 4: All enabled tracks must have their volume and source node referenced
    for s in selections:
        if s.enabled:
            assert f"[aid{s.index}]" in result
            assert f"volume={s.volume:.2f}" in result
