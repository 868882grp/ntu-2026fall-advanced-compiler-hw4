from typing import Dict, Set
from cfg import CFG, BasicBlock


class DominatorTree:
    def __init__(self, cfg: CFG):
        self.cfg = cfg
        self.dom: Dict[BasicBlock, Set[BasicBlock]] = {}
        self.idom: Dict[BasicBlock, BasicBlock] = {}
        self.dom_frontiers: Dict[BasicBlock, Set[BasicBlock]] = {}
        self.compute_dominators()
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
            # TODO: reverse post order
            for bb in self.cfg.blocks.values():
                new_dom = {bb}
                if len(bb.predecessors) == 0:
                    inter_pred_dom = set()
                else:
                    inter_pred_dom = set.intersection(
                        *(self.dom[p] for p in bb.predecessors)
                    )
                new_dom = new_dom | inter_pred_dom
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
                    head = bfs_queue.popleft()
                    if head == bb:
                        pass
                    else:
                        if head in self.dom[bb]:
                            self.idom[bb] = head
                            break
                        else:
                            bfs_queue.extend(head.predecessors)

    def compute_dominance_frontiers(self):
        """
        Computes the dominance frontiers for each basic block.
        """
        # TODO: Implement dominance frontier computation.
        raise NotImplementedError

