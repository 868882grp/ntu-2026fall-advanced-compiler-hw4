from typing import Dict, List, Set

from bril import Function, Instruction, ValueOperation
from cfg import CFG, BasicBlock
from dominance import DominatorTree


def construct_ssa(function: Function):
    """
    Transforms the function into SSA form.
    """
    cfg = CFG(function)
    dom_tree = DominatorTree(cfg)

    # Step 1: Variable Definition Analysis
    defined_in, global_variables = collect_definitions(cfg)

    # Step 2: Insert φ-Functions
    insert_phi_functions(cfg, dom_tree, defined_in, global_variables)

    # Step 3: Rename Variables
    rename_variables(cfg, dom_tree)

    # After transformation, update the function's instructions
    function.instrs = reconstruct_instructions(cfg)


def collect_definitions(cfg: CFG) -> tuple[dict[str, set[BasicBlock]], set[str]]:
    """
    Collects the set of basic blocks in which each variable is defined.
    """
    global_variables: set[str] = set()
    defined_in: dict[str, set[BasicBlock]] = {}
    for bb in cfg.blocks.values():
        varkill: set[BasicBlock] = set()
        for instr in bb.instructions:
            if isinstance(instr, ValueOperation):
                for arg in instr.args:
                    if arg not in varkill:
                        global_variables.add(arg)
                assert instr.dest
                varkill.add(instr.dest)
                defined_in[instr.dest].add(bb)
    return defined_in, global_variables


def insert_phi_functions(
    cfg: CFG,
    dom_tree: DominatorTree,
    defined_in: dict[str, set[BasicBlock]],
    global_variables: set[str],
):
    """
    Inserts φ-functions into the basic blocks.
    """
    import uuid
    from collections import deque

    collision = True
    phi = None
    while collision:
        collision = False
        phi = uuid.uuid4()
        phi_instrs = (
            op for instr in cfg.function.instrs if (op := instr.op) is not None
        )
        for op in phi_instrs:
            if op == phi:
                collision = True

    for var_name in global_variables:
        need_phi_blocks = deque(defined_in[var_name])
        while len(need_phi_blocks) > 0:
            bb = need_phi_blocks.popleft()
            for df in dom_tree.dom_frontiers.get(bb, set()):
                phi_instrs = [
                    instr
                    for instr in df.instructions
                    if isinstance(instr, ValueOperation)
                    and instr.op == phi
                    and all(arg == var_name for arg in instr.args)
                ]
                if len(phi_instrs) > 1:
                    raise AssertionError

                dive = False
                if len(phi_instrs) == 1 and bb.label not in (
                    labels := phi_instrs[0].labels
                ):
                    labels.append(bb.label)
                    dive = True
                elif len(phi_instrs) == 0:
                    # remember to put 'em in the front later
                    df.instructions.append(
                        ValueOperation(
                            {
                                "op": phi,
                                "dest": var_name,
                                "args": var_name,
                                "labels": [bb.label],
                            }
                        ),
                    )
                    dive = True
                if dive:
                    need_phi_blocks.append(df)


def rename_variables(cfg: CFG, dom_tree: DominatorTree):
    """
    Renames variables to ensure each assignment is unique.
    """
    # TODO: Implement variable renaming
    pass


def reconstruct_instructions(cfg: CFG) -> List[Instruction]:
    """
    Reconstructs the instruction list from the CFG after SSA transformation.
    """
    # TODO: Implement instruction reconstruction
    raise NotImplementedError

