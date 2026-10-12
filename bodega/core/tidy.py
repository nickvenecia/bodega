"""Tidy Up Groups: clear, plain group names for film gear, picked by what each piece is.

Gear sheets grow their headings one shoot at a time ("SD Cards", "1000c", "Mech", "Steel"). This sorts every
main piece into a short list of groups a crew would recognise, by reading its name; gear that goes with a
piece follows it. Anything it can't place keeps its group, renamed if the old name has a clearer one.
"""

from __future__ import annotations

import re

from bodega.core.model import Item

# the groups, in the order the list shows them
GROUPS = [
    "Cameras",
    "Lenses",
    "Lens Accessories",
    "Rigging",
    "Media",
    "Storage",
    "Batteries & Power",
    "Monitors & Wireless",
    "Cables",
    "Tripods & Movement",
    "Drones",
    "Lights",
    "Light Modifiers",
    "Grip",
    "Frames & Fabrics",
    "Atmosphere",
    "Audio",
    "Cases & Carts",
    "Computers",
]

# first match wins: (group, words in the name)
RULES: list[tuple[str, str]] = [
    ("Media", r"memory card|cfexpress|\bsd(xc|hc)?\b.*card|\bcard case\b|cfast"),
    ("Storage", r"\bssd\b(?!.*clamp)|\bhdd\b|hard drive(?!.*clamp)|g-drive|external drive"),
    ("Computers", r"macbook|laptop|computer|imac|mac (mini|studio)"),
    ("Drones", r"\bdrone\b|mavic|inspire|\bfpv\b"),
    ("Cameras", r"cinema camera|camera \(body|mirrorless camera|camcorder|\bbody only\b"),
    (
        "Cases & Carts",
        r"hard case|protective case|rifle case|carry-on|wheeled .*case|\bcase,|equipment cart|"
        r"\bcart\b|toolbox|storage tote|\btote\b|carry bag|\bcrate\b",
    ),
    (
        "Audio",
        r"microphone|\bmic\b|boom ?pole|blimp|windshield|lavalier|wireless (receiver|combo|bodypack)|"
        r"\buwp|\burx|\butx|\bsmad|timecode|\bslate\b|\bxlr\b|recorder|headphone",
    ),
    ("Cables", r"\bcable\b"),
    (
        "Monitors & Wireless",
        r"monitor(?!.*mount)|teradek|\bbolt\b.*(rx|tx|receiver|transmitter)|"
        r"wireless video|hollyland",
    ),
    ("Atmosphere", r"fog machine|hazer|\bhaze\b|fogger"),
    (
        "Lens Accessories",
        r"step-up ring|matte box|lens support|lens adapter|follow focus|nucleus|\bnd filter|"
        r"variable nd|diffusion filter|\bfilter\b|anamorphic adapter",
    ),
    ("Lenses", r"\blens\b|\blenses\b|prime|zoom lens|cine lens"),
    (
        "Rigging",
        r"battery plate|rod clamp|drive clamp|ssd.*clamp|\bcage\b|handle|\brod\b|\brods\b|rosette(?!.*gimbal)|"
        r"nato|cold shoe|mounting (bracket|block)|airtag|baseplate",
    ),
    (
        "Batteries & Power",
        r"battery|batteries|power station|generator|stinger|extension cord|power strip|charger",
    ),
    ("Tripods & Movement", r"tripod|dolly|gimbal|stabilizer|car mount|slider|\bjib\b|easyrig|fluid head"),
    ("Lights", r"monolight|\bled\b|tube light|light panel|light mat|infinimat|\blight kit\b|par can"),
    (
        "Light Modifiers",
        r"softbox|light dome|lantern|fresnel|barndoor|reflector|bounce board|lightbridge|"
        r"c-move|grid for|spotlight mount|projection",
    ),
    (
        "Grip",
        r"c-stand|c\+ stand|combo stand|riser stand|baby stand|boom stand|low boy|grip head|grip arm|wheel|"
        r"clamp|apple box|shotbag|sandbag|menace arm|pipe|spring link|tennis ball|matthellini|quacker|"
        r"multiclip|\bstand\b",
    ),
    (
        "Frames & Fabrics",
        r"frame|grid cloth|muslin|ultrabounce|bounce|\bsolid\b|camo net|\bnet\b|scrim|flag kit|"
        r"\brag\b|griffolyn|silk",
    ),
    ("Rigging", r"\bplate\b|\barm\b|top handle|side handle"),
]

# old group names with a clearer one (used when nothing in the name decides)
RENAMES = {
    "body": "Cameras",
    "bodies": "Cameras",
    "camera": "Cameras",
    "sd cards": "Media",
    "media": "Media",
    "cards": "Media",
    "ssds": "Storage",
    "hds": "Storage",
    "hard drives": "Storage",
    "drives": "Storage",
    "computers": "Computers",
    "batteries": "Batteries & Power",
    "power": "Batteries & Power",
    "generator": "Batteries & Power",
    "stingers": "Batteries & Power",
    "(wireless) monitoring": "Monitors & Wireless",
    "monitoring": "Monitors & Wireless",
    "monitors": "Monitors & Wireless",
    "mech": "Tripods & Movement",
    "support": "Rigging",
    "drone": "Drones",
    "1000c": "Lights",
    "80c": "Lights",
    "tube lights": "Lights",
    "mc pro": "Lights",
    "b7c": "Lights",
    "infinimat": "Lights",
    "lights": "Lights",
    "softbox": "Light Modifiers",
    "reflectors": "Light Modifiers",
    "frames & rags": "Frames & Fabrics",
    "scrims & flags": "Frames & Fabrics",
    "steel": "Grip",
    "clips & clamps": "Grip",
    "apple boxes": "Grip",
    "shotbags": "Grip",
    "padding": "Grip",
    "menace arm": "Grip",
    "hazers": "Atmosphere",
    "crates": "Cases & Carts",
    "cases": "Cases & Carts",
    "slate": "Audio",
    "microphones": "Audio",
    "audio accessories": "Audio",
    "sony uwp": "Audio",
}


def group_for(item: Item) -> str:
    """The tidy group for one piece, by its name (then by its old group)."""
    name = item.name.lower()
    for group, pattern in RULES:
        if re.search(pattern, name):
            return group
    return RENAMES.get(item.group.strip().lower(), item.group)


def suggest(items: dict[str, Item]) -> dict[str, str]:
    """item id -> the group it would go in. Gear that goes with a piece follows that piece."""
    out: dict[str, str] = {}
    for it in items.values():
        if not (it.parent and it.parent in items):
            out[it.id] = group_for(it)
    for it in items.values():
        if it.id in out:
            continue
        root, seen = it, {it.id}
        while root.parent and root.parent in items and root.parent not in seen:
            seen.add(root.parent)
            root = items[root.parent]
        out[it.id] = out.get(root.id) or group_for(it)
    return out


def changes(items: dict[str, Item]) -> list[tuple[Item, str, str]]:
    """(item, from, to) for every piece whose group would change."""
    new = suggest(items)
    return [(it, it.group, new[it.id]) for it in items.values() if new[it.id] != it.group]
