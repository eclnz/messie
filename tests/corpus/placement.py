"""Ground-truth trees for optional folder placement analysis.

Each case labels every placement finding expected in its isolated tree. Folder
names here describe the fixture; the implementation has no rules for them.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from corpus import TOPICS
from corpus.build import add_topic
from corpus.synth import write_plain


@dataclass(frozen=True)
class PlacementCase:
    name: str
    build: Callable[[Path], dict[str, str]]


def _nested_checks(root: Path) -> dict[str, str]:
    """Feature-specific checks sit under source instead of the existing checks tree."""
    nested = root / "src" / "invoice" / "checks"
    destination = root / "tests"
    for index in range(6):
        write_plain(
            root / "src" / "invoice" / f"pricing_{index}.py",
            (
                f"def calculate_invoice_total_{index}(items, tax_rate):\n"
                "    subtotal = sum(item.price * item.quantity for item in items)\n"
                "    tax = subtotal * tax_rate\n"
                "    return subtotal + tax\n"
            ) * 4,
        )
        write_plain(
            nested / f"check_{index}.py",
            (
                f"def test_invoice_total_{index}():\n"
                "    items = make_items()\n"
                "    assert calculate_invoice_total(items, 0.1) == expected_total\n"
            ) * 5,
        )
        write_plain(
            destination / f"check_{index}.py",
            (
                f"def test_cart_discount_{index}():\n"
                "    cart = make_cart()\n"
                "    assert apply_discount(cart, 0.1) == expected_cart\n"
            ) * 5,
        )
    return {"src/invoice/checks": "tests"}


def _misplaced_documents(root: Path) -> dict[str, str]:
    """A coherent document subtree is under an unrelated subject."""
    add_topic(root / "Work" / "Stories", "novel_manuscript", 8, kinds=("txt",))
    add_topic(root / "Work" / "Stories" / "Bundle", "tax_return", 8, kinds=("txt",))
    add_topic(root / "Accounts", "tax_return", 8, seed=1, kinds=("txt",))
    return {"Work/Stories/Bundle": "Accounts"}


def _mixed_subtree(root: Path) -> dict[str, str]:
    """Two retained subjects together match a destination with both subjects."""
    candidate = root / "Work" / "Bundle"
    destination = root / "Archive"
    add_topic(root / "Work", "garden_planting_notes", 12, kinds=("txt",))
    for topic in ("tax_return", "novel_manuscript"):
        add_topic(candidate, topic, 4, kinds=("txt",))
        add_topic(destination, topic, 6, seed=1, kinds=("txt",))
    return {"Work/Bundle": "Archive"}


def _clean_siblings(root: Path) -> dict[str, str]:
    """Distinct sibling subjects do not imply that one should move."""
    for folder, topic in (
        ("Accounts", "tax_return"),
        ("Books", "novel_manuscript"),
        ("Kitchen", "baking_recipes"),
    ):
        add_topic(root / folder, topic, 8, kinds=("txt",))
    return {}


def _locally_supported_duplicate(root: Path) -> dict[str, str]:
    """An alternative with the same subject does not beat strong local support."""
    add_topic(root / "Projects", "tax_return", 8, kinds=("txt",))
    add_topic(root / "Projects" / "Bundle", "tax_return", 8, seed=1,
              kinds=("txt",))
    add_topic(root / "Accounts", "tax_return", 8, seed=2, kinds=("txt",))
    return {}


def _one_topic_decoy(root: Path) -> dict[str, str]:
    """One matching part cannot justify moving a mixed subtree."""
    add_topic(root / "Projects", "garden_planting_notes", 8, kinds=("txt",))
    add_topic(root / "Projects" / "Bundle", "tax_return", 4, kinds=("txt",))
    add_topic(root / "Projects" / "Bundle", "novel_manuscript", 4,
              kinds=("txt",))
    add_topic(root / "Accounts", "tax_return", 8, seed=1, kinds=("txt",))
    return {}


def _tiny_current_context(root: Path) -> dict[str, str]:
    """A few incidental files cannot define the candidate's current location."""
    add_topic(root / "Work", "garden_planting_notes", 3, kinds=("txt",))
    add_topic(root / "Work" / "Bundle", "tax_return", 12, kinds=("txt",))
    add_topic(root / "Accounts", "tax_return", 12, seed=1, kinds=("txt",))
    return {}


def _shared_names_wrong_subject(root: Path) -> dict[str, str]:
    """Identical file-name patterns must not override different contents."""
    for folder, topic in (
        (root / "Work", "baking_recipes"),
        (root / "Work" / "Bundle", "tax_return"),
        (root / "Archive", "novel_manuscript"),
    ):
        entries = TOPICS[topic]
        for index in range(8):
            text = entries[index % len(entries)][1]
            write_plain(folder / f"record_{index}.txt", text)
    return {}


PLACEMENT_CASES = (
    PlacementCase("nested_checks", _nested_checks),
    PlacementCase("misplaced_documents", _misplaced_documents),
    PlacementCase("mixed_subtree", _mixed_subtree),
    PlacementCase("clean_siblings", _clean_siblings),
    PlacementCase("locally_supported_duplicate", _locally_supported_duplicate),
    PlacementCase("one_topic_decoy", _one_topic_decoy),
    PlacementCase("tiny_current_context", _tiny_current_context),
    PlacementCase("shared_names_wrong_subject", _shared_names_wrong_subject),
)
