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

from bril import Program, parse_bril  # noqa: E402
from cfg import BasicBlock, CFG  # noqa: E402


def load_bril_file(path: Path) -> Program:
    res = subprocess.run(
        ["bril2json"],
        input=path.read_bytes(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return parse_bril(res.stdout.decode("utf-8"))


def block_name(bb: BasicBlock) -> str:
    # Unnamed entry blocks have bb.label == "" (and a random UUID key in cfg.blocks)
    return bb.label if bb.label else "<entry>"


def snapshot_cfg(cfg: CFG) -> dict[str, dict]:
    return {
        block_name(bb): {
            "instr_count": len(bb.instructions),
            "preds": sorted(block_name(p) for p in bb.predecessors),
            "succs": sorted(block_name(s) for s in bb.successors),
        }
        for bb in cfg.get_blocks()
    }


# Expected CFGs derived directly from tests/*.bril
# Format: { filename: { func_name: { block_label: {instr_count, preds, succs} } } }
EXPECTED_CFGS = {
    "simple.bril": {
        "main": {
            "<entry>": {"instr_count": 8, "preds": [], "succs": []},
        },
    },
    "loop.bril": {
        "main": {
            "entry": {"instr_count": 3, "preds": [], "succs": ["loop"]},
            "loop": {
                "instr_count": 4,
                "preds": ["body", "entry"],
                "succs": ["body", "exit"],
            },
            "body": {"instr_count": 3, "preds": ["loop"], "succs": ["loop"]},
            "exit": {"instr_count": 2, "preds": ["loop"], "succs": []},
        },
    },
    "self_loop.bril": {
        "main": {
            "entry": {"instr_count": 4, "preds": [], "succs": ["loop"]},
            "loop": {"instr_count": 3, "preds": ["br", "entry"], "succs": ["br"]},
            "br": {"instr_count": 2, "preds": ["loop"], "succs": ["exit", "loop"]},
            "exit": {"instr_count": 3, "preds": ["br"], "succs": []},
        },
    },
    "while.bril": {
        "main": {
            "while.cond": {
                "instr_count": 4,
                "preds": ["while.body"],
                "succs": ["while.body", "while.finish"],
            },
            "while.body": {
                "instr_count": 4,
                "preds": ["while.cond"],
                "succs": ["while.cond"],
            },
            "while.finish": {"instr_count": 2, "preds": ["while.cond"], "succs": []},
        },
    },
    "diamond.bril": {
        "main": {
            "<entry>": {"instr_count": 5, "preds": [], "succs": ["else", "then"]},
            "then": {
                "instr_count": 4,
                "preds": ["<entry>"],
                "succs": ["inner", "join"],
            },
            "inner": {"instr_count": 4, "preds": ["then"], "succs": ["join"]},
            "else": {"instr_count": 3, "preds": ["<entry>"], "succs": ["join"]},
            "join": {"instr_count": 4, "preds": ["else", "inner", "then"], "succs": []},
        },
    },
    "example.bril": {
        "main": {
            "b0": {"instr_count": 2, "preds": [], "succs": ["b1"]},
            "b1": {"instr_count": 5, "preds": ["b0", "b3"], "succs": ["b2", "b5"]},
            "b2": {"instr_count": 5, "preds": ["b1"], "succs": ["b3"]},
            "b3": {"instr_count": 8, "preds": ["b2", "b7"], "succs": ["b1", "b4"]},
            "b4": {"instr_count": 2, "preds": ["b3"], "succs": []},
            "b5": {"instr_count": 5, "preds": ["b1"], "succs": ["b6", "b8"]},
            "b6": {"instr_count": 3, "preds": ["b5"], "succs": ["b7"]},
            "b7": {"instr_count": 3, "preds": ["b6", "b8"], "succs": ["b3"]},
            "b8": {"instr_count": 3, "preds": ["b5"], "succs": ["b7"]},
        },
    },
    "factors.bril": {
        "main": {
            "<entry>": {"instr_count": 3, "preds": [], "succs": ["loopcheck"]},
            "loopcheck": {
                "instr_count": 3,
                "preds": ["<entry>", "ifno", "ifyes"],
                "succs": ["loopbody", "loopend"],
            },
            "loopbody": {
                "instr_count": 6,
                "preds": ["loopcheck"],
                "succs": ["ifno", "ifyes"],
            },
            "ifyes": {"instr_count": 4, "preds": ["loopbody"], "succs": ["loopcheck"]},
            "ifno": {"instr_count": 3, "preds": ["loopbody"], "succs": ["loopcheck"]},
            "loopend": {"instr_count": 1, "preds": ["loopcheck"], "succs": []},
        },
    },
    "gcd_sum.bril": {
        "main": {
            "<entry>": {"instr_count": 3, "preds": [], "succs": ["outer"]},
            "outer": {
                "instr_count": 3,
                "preds": ["<entry>", "inner.done"],
                "succs": ["done", "outer.body"],
            },
            "outer.body": {"instr_count": 2, "preds": ["outer"], "succs": ["inner"]},
            "inner": {
                "instr_count": 3,
                "preds": ["inner.body", "outer.body"],
                "succs": ["inner.body", "inner.done"],
            },
            "inner.body": {"instr_count": 5, "preds": ["inner"], "succs": ["inner"]},
            "inner.done": {"instr_count": 3, "preds": ["inner"], "succs": ["outer"]},
            "done": {"instr_count": 2, "preds": ["outer"], "succs": []},
        },
        "gcd": {
            "<entry>": {"instr_count": 1, "preds": [], "succs": ["loop"]},
            "loop": {
                "instr_count": 3,
                "preds": ["<entry>", "body"],
                "succs": ["body", "end"],
            },
            "body": {"instr_count": 7, "preds": ["loop"], "succs": ["loop"]},
            "end": {"instr_count": 2, "preds": ["loop"], "succs": []},
        },
    },
}


@unittest.skipUnless(shutil.which("bril2json"), "bril2json must be on PATH")
class TestCFGAgainstBrilFiles(unittest.TestCase):
    def test_expected_cfgs(self) -> None:
        for filename, expected_funcs in EXPECTED_CFGS.items():
            with self.subTest(file=filename):
                prog = load_bril_file(TESTS_DIR / filename)
                self.assertEqual(
                    [f.name for f in prog.functions], list(expected_funcs.keys())
                )
                for func in prog.functions:
                    cfg = CFG(func)
                    assert func.name
                    self.assertEqual(snapshot_cfg(cfg), expected_funcs[func.name])
