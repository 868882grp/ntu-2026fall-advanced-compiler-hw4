from typing import Dict, Set

from cfg import CFG, BasicBlock


class DominatorTree:
    def __init__(self, cfg: CFG):
        self.cfg = cfg
        self.dom: Dict[BasicBlock, Set[BasicBlock]] = {}
        self.idom: Dict[BasicBlock, BasicBlock] = {}
        self.dom_frontiers: Dict[BasicBlock, Set[BasicBlock]] = {}
        self.compute_dominators()
        self.compute_idom()
        self.compute_dominance_frontiers()

    def compute_dominators(self):
        """
        Computes the dominators for each basic block.
        """
        self.dom.clear()

        for i, bb in enumerate(self.cfg.blocks.values()):
            if i == 0:
                self.dom[bb] = {bb}
            else:
                self.dom[bb] = set(self.cfg.blocks.values())

        iterating = True
        while iterating:
            iterating = False
            # Ignore entry block: all other blocks has well-defined predecessors,
            # and entry block dominator is always but itself anyway
            #
            # TODO: reverse post order
            blocks = iter(self.cfg.blocks.values())
            next(blocks)
            for bb in blocks:
                inter_pred_dom = set.intersection(
                    *(self.dom[p] for p in bb.predecessors)
                )
                new_dom = {bb} | inter_pred_dom
                if new_dom != self.dom[bb]:
                    self.dom[bb] = new_dom
                    iterating = True

    def compute_idom(self):
        """
        Computes the immediate dominator for each basic block.
        Assumes dominators are already calculated
        """
        from collections import deque

        self.idom.clear()
        for bb in self.cfg.blocks.values():
            if self.dom[bb] == set() or self.dom[bb] == {bb}:
                pass
            else:
                bfs_queue: deque[BasicBlock] = deque(bb.predecessors)
                while len(bfs_queue) != 0:
                    ptr = bfs_queue.popleft()
                    if ptr == bb:
                        pass
                    else:
                        if ptr in self.dom[bb]:
                            self.idom[bb] = ptr
                            break
                        else:
                            bfs_queue.extend(ptr.predecessors)

    def compute_dominance_frontiers(self):
        """
        Computes the dominance frontiers for each basic block.
        Assumes both dominator and immediate dominator already calculated.
        """
        self.dom_frontiers.clear()
        for bb in self.cfg.blocks.values():
            if len(bb.predecessors) > 1:
                for pred in bb.predecessors:
                    ptr = pred
                    # BB has multiple predecessor,
                    # meaning immediate dominator shall be well-defined
                    while ptr != self.idom[bb]:
                        self.dom_frontiers[ptr] = self.dom_frontiers.get(ptr, set()) | {
                            bb
                        }
                        ptr = self.idom[ptr]
