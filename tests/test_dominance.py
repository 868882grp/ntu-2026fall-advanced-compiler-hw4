import shutil
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
TESTS_DIR = REPO_ROOT / "tests"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from bril import Function, parse_bril  # noqa: E402
from cfg import CFG, BasicBlock  # noqa: E402
from dominance import DominatorTree  # noqa: E402


def make_func(instrs: list[dict], name: str = "main") -> Function:
    return Function({"name": name, "instrs": instrs})


def block_name(bb: BasicBlock) -> str:
    return bb.label if bb.label else "<entry>"


def snapshot_dom(dom_tree: DominatorTree) -> dict[str, set[str]]:
    return {
        block_name(bb): {block_name(d) for d in doms}
        for bb, doms in dom_tree.dom.items()
    }


class TestDominatorsSynthetic(unittest.TestCase):
    def test_single_block(self) -> None:
        cfg = CFG(make_func([{"op": "ret"}]))
        dt = DominatorTree(cfg)
        self.assertEqual(snapshot_dom(dt), {"<entry>": {"<entry>"}})

    def test_diamond(self) -> None:
        cfg = CFG(
            make_func(
                [
                    {"label": "entry"},
                    {"op": "br", "args": ["c"], "labels": ["left", "right"]},
                    {"label": "left"},
                    {"op": "jmp", "labels": ["join"]},
                    {"label": "right"},
                    {"op": "jmp", "labels": ["join"]},
                    {"label": "join"},
                    {"op": "ret"},
                ]
            )
        )
        dt = DominatorTree(cfg)
        self.assertEqual(
            snapshot_dom(dt),
            {
                "entry": {"entry"},
                "left": {"entry", "left"},
                "right": {"entry", "right"},
                "join": {"entry", "join"},
            },
        )

    def test_loop_with_preheader(self) -> None:
        # Catches initializing non-entry blocks to {bb} instead of all_blocks
        cfg = CFG(
            make_func(
                [
                    {"label": "entry"},
                    {"op": "jmp", "labels": ["loop"]},
                    {"label": "loop"},
                    {"op": "br", "args": ["c"], "labels": ["body", "exit"]},
                    {"label": "body"},
                    {"op": "jmp", "labels": ["loop"]},
                    {"label": "exit"},
                    {"op": "ret"},
                ]
            )
        )
        dt = DominatorTree(cfg)
        self.assertEqual(
            snapshot_dom(dt),
            {
                "entry": {"entry"},
                "loop": {"entry", "loop"},
                "body": {"entry", "loop", "body"},
                "exit": {"entry", "loop", "exit"},
            },
        )

    def test_entry_is_loop_header(self) -> None:
        # Catches recomputing dom[entry] from a backedge / initializing entry to all_blocks
        cfg = CFG(
            make_func(
                [
                    {"label": "head"},
                    {"op": "br", "args": ["c"], "labels": ["body", "exit"]},
                    {"label": "body"},
                    {"op": "jmp", "labels": ["head"]},
                    {"label": "exit"},
                    {"op": "ret"},
                ]
            )
        )
        dt = DominatorTree(cfg)
        self.assertEqual(
            snapshot_dom(dt),
            {
                "head": {"head"},
                "body": {"head", "body"},
                "exit": {"head", "exit"},
            },
        )

    def test_irreducible_like_two_entry_join_and_nested_branch(self) -> None:
        # entry -> a -> join, entry -> b -> join, join -> b (backedge)
        cfg = CFG(
            make_func(
                [
                    {"label": "entry"},
                    {"op": "br", "args": ["c"], "labels": ["a", "b"]},
                    {"label": "a"},
                    {"op": "jmp", "labels": ["join"]},
                    {"label": "b"},
                    {"op": "jmp", "labels": ["join"]},
                    {"label": "join"},
                    {"op": "br", "args": ["d"], "labels": ["b", "exit"]},
                    {"label": "exit"},
                    {"op": "ret"},
                ]
            )
        )
        dt = DominatorTree(cfg)
        self.assertEqual(
            snapshot_dom(dt),
            {
                "entry": {"entry"},
                "a": {"entry", "a"},
                "b": {"entry", "b"},
                "join": {"entry", "join"},
                "exit": {"entry", "join", "exit"},
            },
        )


EXPECTED_DOMS = {
    "simple.bril": {
        "main": {"<entry>": {"<entry>"}},
    },
    "diamond.bril": {
        "main": {
            "<entry>": {"<entry>"},
            "then": {"<entry>", "then"},
            "inner": {"<entry>", "then", "inner"},
            "else": {"<entry>", "else"},
            "join": {"<entry>", "join"},
        },
    },
    "loop.bril": {
        "main": {
            "entry": {"entry"},
            "loop": {"entry", "loop"},
            "body": {"entry", "loop", "body"},
            "exit": {"entry", "loop", "exit"},
        },
    },
    "while.bril": {
        "main": {
            "while.cond": {"while.cond"},
            "while.body": {"while.cond", "while.body"},
            "while.finish": {"while.cond", "while.finish"},
        },
    },
    "self_loop.bril": {
        "main": {
            "entry": {"entry"},
            "loop": {"entry", "loop"},
            "br": {"entry", "loop", "br"},
            "exit": {"entry", "loop", "br", "exit"},
        },
    },
    # Fig. 9.13 from "Engineering a Compiler"
    "example.bril": {
        "main": {
            "b0": {"b0"},
            "b1": {"b0", "b1"},
            "b2": {"b0", "b1", "b2"},
            "b3": {"b0", "b1", "b3"},
            "b4": {"b0", "b1", "b3", "b4"},
            "b5": {"b0", "b1", "b5"},
            "b6": {"b0", "b1", "b5", "b6"},
            "b7": {"b0", "b1", "b5", "b7"},
            "b8": {"b0", "b1", "b5", "b8"},
        },
    },
}


@unittest.skipUnless(shutil.which("bril2json"), "bril2json must be on PATH")
class TestDominatorsFromBrilFiles(unittest.TestCase):
    def test_expected_dominators(self) -> None:
        for filename, expected_funcs in EXPECTED_DOMS.items():
            with self.subTest(file=filename):
                res = subprocess.run(
                    ["bril2json"],
                    input=(TESTS_DIR / filename).read_bytes(),
                    capture_output=True,
                    check=True,
                )
                prog = parse_bril(res.stdout.decode("utf-8"))
                for func in prog.functions:
                    cfg = CFG(func)
                    dt = DominatorTree(cfg)
                    assert func.name
                    self.assertEqual(snapshot_dom(dt), expected_funcs[func.name])
