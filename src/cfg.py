from typing import Dict, List, Set

from bril import Const, EffectOperation, Function, Instruction, Label, ValueOperation


class BasicBlock:
    def __init__(self, label: str):
        self.label = label
        self.instructions: List[Instruction] = []
        self.predecessors: Set["BasicBlock"] = set()
        self.successors: Set["BasicBlock"] = set()

    def __repr__(self):
        return f"BasicBlock({self.label})"


class CFG:
    def __init__(self, function: Function):
        self.function = function
        self.blocks: Dict[str, BasicBlock] = {}
        self.entry_block: BasicBlock = self.construct_cfg()

    def construct_cfg(self) -> BasicBlock:
        """
        Constructs the CFG for the function and returns the entry block.
        """
        import uuid

        # TODO: Implement CFG construction logic
        # Steps:
        # 1. Divide instructions into basic blocks.
        # 2. Establish successor and predecessor relationships.
        # 3. Handle labels and control flow instructions.

        # sane check: labels shall be nonempty and unique
        known_labels = set()
        for instr in self.function.instrs:
            if isinstance(instr, Label):
                if not instr.label:
                    raise ValueError(f"Rejecting none/empty label: {instr!r}")
                if instr.label in known_labels:
                    raise ValueError(f"Duplicate label found: {instr!r}")
                known_labels.add(instr.label)

        while True:
            collision = False
            self.blocks = {}
            for bb in form_blocks(self.function.instrs):
                key = bb.label if bb.label else str(uuid.uuid4())
                if key in self.blocks:
                    collision = True
                    break
                self.blocks[key] = bb
            if not collision:
                break

        for bb in self.blocks.values():
            last_instr = bb.instructions[-1]
            if isinstance(last_instr, EffectOperation):
                if last_instr.op == "jmp" or last_instr.op == "br":
                    for label in last_instr.labels:
                        self.blocks[label].predecessors.add(bb)
                        bb.successors.add(self.blocks[label])
                else:
                    pass

        return next(iter(self.blocks.values()))

    def get_blocks(self) -> List[BasicBlock]:
        return list(self.blocks.values())


# Parses instructions into blocks, also handles linear control flow;
# branches and jumps are not handled
#
# TODO: handle BEQ?
def form_blocks(instrs: list[Instruction]):
    bb = BasicBlock("")
    for instr in instrs:
        if isinstance(instr, Label):
            # start of new BB...
            pred = bb
            assert instr.label, "sanitize labels first!"
            bb = BasicBlock(instr.label)
            bb.instructions.append(instr)
            # the BB is cut here due to labels,
            # meaning the last line is our predecessor: linear control flow
            if len(pred.instructions) == 0:
                # If Bril were to have BEQ,
                # we'd need to handle its linear control case here,
                # for retrieving its "fall through" BB later would be more troublesome
                #
                # In basic Bril all jumps have labels, though.
                pass
            else:
                bb.predecessors.add(pred)
                pred.successors.add(bb)
                yield pred
        elif isinstance(instr, (ValueOperation, Const)):
            bb.instructions.append(instr)
        elif isinstance(instr, EffectOperation):
            # check if it's terminator, if so, mark BB end
            TERMINATORS = "br", "jmp", "ret"
            bb.instructions.append(instr)
            if instr.op in TERMINATORS:
                ret = bb
                bb = BasicBlock("")
                yield ret
        else:
            raise NotImplementedError
    if len(bb.instructions) != 0:
        yield bb
