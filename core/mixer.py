from core.types import MixSelection


def build_lavfi_complex(selections: list[MixSelection]) -> str:
    """
    Builds a lavfi complex filter graph string for mixing multiple audio tracks.

    Args:
        selections: A list of MixSelection objects containing index, volume, and enabled state.

    Returns:
        A lavfi filter string ready to be passed to mpv's lavfi-complex option.
    """
    enabled_selections = [s for s in selections if s.enabled]

    # If no tracks are enabled, return a silent audio source
    if not enabled_selections:
        return "anullsrc[ao]"

    # If only one track is enabled, apply volume and pipe directly to output
    if len(enabled_selections) == 1:
        sel = enabled_selections[0]
        return f"[aid{sel.index}]volume={sel.volume:.2f}[ao]"

    nodes: list[str] = []
    inputs: list[str] = []

    # Apply volume to each enabled track and route them to temporary labels
    for i, sel in enumerate(enabled_selections):
        node_in = f"[aid{sel.index}]"
        node_out = f"[a{i}]"
        nodes.append(f"{node_in}volume={sel.volume:.2f}{node_out}")
        inputs.append(node_out)

    # Mix all the temporary streams together
    inputs_str = "".join(inputs)
    mix_node = f"{inputs_str}amix=inputs={len(inputs)}:duration=longest[ao]"
    nodes.append(mix_node)

    return ";".join(nodes)
