"""What a footprint is, worked out from its own geometry and text, and the description and tags made from it (FLD-03).

Nothing is guessed: a pitch, body size or package family that cannot be computed or read is left out
of the sentence and the tags (D-28). The module only reads parsed nodes; the write goes through
kicad_files.footprint_text_edit and sexpr.apply_edits.
"""

import math
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from ..kicad_files import footprint_text_node
from ..sexpr import Node, unquote

# A footprint with more numbered pads than this gets no pitch: the nearest-neighbour scan is quadratic
_MAX_PITCH_PADS = 2000
_FAB_LAYER = "F.Fab"
_COURTYARD_LAYER = "F.CrtYd"
_OUTLINE_HEADS = ("fp_line", "fp_rect", "fp_poly", "fp_circle", "fp_arc")
_POINT_HEADS = ("start", "end", "mid", "center")

_FAMILIES = (
    "SOIC|VSSOP|SSOP|TSSOP|MSOP|VQFN|WQFN|QFN|DFN|WSON|VSON|USON|SON|LGA|BGA|LQFP|TQFP|QFP|DIP|SIP"
)
_SOT_BASES = "223|23|323|363|563|89"
_NOT_IN_WORD = r"(?<![A-Za-z0-9])"
_PINNED_RE = re.compile(_NOT_IN_WORD + rf"({_FAMILIES})-?(\d{{1,3}})(?![0-9])", re.IGNORECASE)
_SOT_RE = re.compile(_NOT_IN_WORD + rf"SOT-?({_SOT_BASES})(?![0-9])(?:-(\d{{1,2}})(?![0-9]))?", re.IGNORECASE)


@dataclass(frozen=True)
class FootprintFacts:
    """What is known about a footprint; None means it could not be worked out."""

    pads: int
    pitch: float | None
    body: tuple[float, float] | None
    family: str | None
    code: str
    maker: str


def _token_text(node: Node) -> str | None:
    """The unquoted text of a string or atom node, None for a list."""
    return unquote(node.text) if node.kind in ("str", "atom") else None


def _number(node: Node) -> float | None:
    """The finite float of an atom node, or None."""
    if node.kind != "atom":
        return None
    try:
        value = float(node.text)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def _point(node: Node) -> tuple[float, float] | None:
    """The (x, y) of a list such as (at x y ...) or (xy x y), or None when it holds no two numbers."""
    if len(node.children) < 3:
        return None
    x, y = _number(node.children[1]), _number(node.children[2])
    if x is None or y is None:
        return None
    return x, y


# ── Geometry ──────────────────────────────────────────────────────────────────


def pad_centres(footprint_node: Node) -> list[tuple[float, float]]:
    """Centres of the footprint's numbered pads.

    Pads with an empty number and non-plated holes (np_thru_hole) are ignored, as in
    verify.footprint_pad_numbers; a pad without a readable (at x y) is skipped.
    """
    centres = []
    for child in footprint_node.children:
        if child.head != "pad" or len(child.children) < 2:
            continue
        if len(child.children) >= 3 and _token_text(child.children[2]) == "np_thru_hole":
            continue
        if not _token_text(child.children[1]):
            continue
        at = next((c for c in child.children if c.head == "at"), None)
        centre = _point(at) if at is not None else None
        if centre is not None:
            centres.append(centre)
    return centres


def pitch_mm(centres: Sequence[tuple[float, float]]) -> float | None:
    """The smallest nearest-neighbour centre distance that occurs at least twice, rounded to 0.01 mm.

    Pads stacked on the same centre count once; fewer than two distinct centres, no repeated distance,
    or more than _MAX_PITCH_PADS pads give None.
    """
    distinct = list(dict.fromkeys((round(x, 4), round(y, 4)) for x, y in centres))
    if len(distinct) < 2 or len(distinct) > _MAX_PITCH_PADS:
        return None
    nearest = [
        round(min(math.dist(a, b) for j, b in enumerate(distinct) if j != i), 2)
        for i, a in enumerate(distinct)
    ]
    repeated = [d for d, n in Counter(nearest).items() if n >= 2 and d > 0]
    return min(repeated) if repeated else None


def _layer_name(node: Node) -> str | None:
    layer = next((c for c in node.children if c.head == "layer"), None)
    if layer is None or len(layer.children) < 2:
        return None
    return _token_text(layer.children[1])


def _outline_points(node: Node) -> list[tuple[float, float]]:
    """Every point of one graphic item; a circle contributes the box of its radius."""
    points = []
    for part in node.children[1:]:
        if part.head in _POINT_HEADS:
            point = _point(part)
            if point is not None:
                points.append(point)
        elif part.head == "pts":
            points.extend(p for p in (_point(xy) for xy in part.children[1:] if xy.head == "xy") if p is not None)
    if node.head == "fp_circle" and len(points) >= 2:
        (cx, cy), (ex, ey) = points[0], points[1]
        radius = math.dist((cx, cy), (ex, ey))
        points = [(cx - radius, cy - radius), (cx + radius, cy + radius)]
    return points


def _layer_box(footprint_node: Node, layer: str) -> tuple[float, float] | None:
    """Width and height of the bounding box of the graphics on one layer, or None without an area."""
    xs: list[float] = []
    ys: list[float] = []
    for child in footprint_node.children:
        if child.head in _OUTLINE_HEADS and _layer_name(child) == layer:
            for x, y in _outline_points(child):
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    width, height = round(max(xs) - min(xs), 1), round(max(ys) - min(ys), 1)
    if width <= 0 or height <= 0:
        return None
    return width, height


def body_mm(footprint_node: Node) -> tuple[float, float] | None:
    """Body size from the F.Fab outline, rounded to 0.1 mm; the courtyard only when there is no Fab outline.

    The courtyard includes clearance and overstates the body, so it is a fallback, never a check.
    """
    return _layer_box(footprint_node, _FAB_LAYER) or _layer_box(footprint_node, _COURTYARD_LAYER)


# ── Text ──────────────────────────────────────────────────────────────────────


def package_family(texts: Sequence[str]) -> str | None:
    """The package family named in the texts, as "<FAMILY>-<pins>" (WSON6 gives WSON-6), or None.

    Only a closed list of families is recognised and the pin count is the one written in the text, never
    the pad count. The first text that names a family wins.
    """
    for text in texts:
        found = []
        pinned = _PINNED_RE.search(text)
        if pinned:
            found.append((pinned.start(), f"{pinned[1].upper()}-{pinned[2]}"))
        sot = _SOT_RE.search(text)
        if sot:
            found.append((sot.start(), f"SOT-{sot[1]}" + (f"-{sot[2]}" if sot[2] else "")))
        if found:
            return min(found)[1]
    return None


def vendor_texts(footprint_node: Node) -> tuple[str, str]:
    """The footprint's own (descr, tags) strings; "" for one that is absent."""
    def value(key: str) -> str:
        token = footprint_text_node(footprint_node, key)
        return (_token_text(token) or "") if token is not None else ""

    return value("descr"), value("tags")


def footprint_facts(
    footprint_node: Node, *, code: str, maker: str, texts: Sequence[str] = ()
) -> FootprintFacts:
    """Collect the facts of a footprint; the family is read from its own descr and tags, then from texts."""
    descr, tags = vendor_texts(footprint_node)
    centres = pad_centres(footprint_node)
    return FootprintFacts(
        pads=len(centres),
        pitch=pitch_mm(centres),
        body=body_mm(footprint_node),
        family=package_family([descr, tags, *texts]),
        code=code,
        maker=maker,
    )


# ── Sentence and tags ─────────────────────────────────────────────────────────


def _num(value: float, digits: int) -> str:
    """Print a number rounded to digits decimals without trailing zeros (0.5, 1.27, 2)."""
    return f"{round(value, digits):.{digits}f}".rstrip("0").rstrip(".")


def _one_line(value: str) -> str:
    return " ".join(value.split())


def _body_text(facts: FootprintFacts) -> str:
    if facts.body is None:
        return ""
    return f"{_num(facts.body[0], 1)}x{_num(facts.body[1], 1)}"


def _pitch_text(facts: FootprintFacts) -> str:
    return _num(facts.pitch, 2) if facts.pitch is not None else ""


def ipc_name(facts: FootprintFacts) -> str | None:
    """KiCad's IPC-style name <Family>_<W>x<H>mm_P<pitch>mm, only when family, body and pitch are all known."""
    if facts.family is None or facts.body is None or facts.pitch is None:
        return None
    return f"{facts.family}_{_body_text(facts)}mm_P{_pitch_text(facts)}mm"


def describe(facts: FootprintFacts) -> str:
    """One plain sentence about the footprint; whatever could not be worked out is left out."""
    package = " ".join(p for p in (facts.family, f"{_body_text(facts)} mm" if facts.body else "") if p)
    pitch = f"{_pitch_text(facts)} mm pitch" if facts.pitch is not None else ""
    maker = " ".join(p for p in (_one_line(facts.maker), _one_line(facts.code)) if p)
    return ", ".join(part for part in (package, pitch, maker) if part)


def generated_tags(facts: FootprintFacts) -> list[str]:
    """Tags worth adding: family, IPC-style name, package code and pitch, each only when known."""
    tags = [facts.family, ipc_name(facts), "_".join(facts.code.split()) or None]
    if facts.pitch is not None:
        tags.append(f"P{_pitch_text(facts)}mm")
    return [tag for tag in tags if tag]
