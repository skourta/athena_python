from __future__ import annotations

import copy
import itertools
from typing import Dict, List, Tuple

from tiralib.tiramisu.tiramisu_iterator_node import IteratorIdentifier
from tiralib.tiramisu.tiramisu_tree import TiramisuTree


from tiralib.tiramisu.tiramisu_actions.tiramisu_action import (
    TiramisuAction,
    TiramisuActionType,
)


class Tiling3D(TiramisuAction):
    """
    3D Tiling optimization command.
    """

    def __init__(
        self,
        params: List[IteratorIdentifier | int],
        comps: List[str] | None = None,
    ):
        # 3D Tiling takes six parameters divided into three tuples:
        # 1. The first iterator to tile
        # 2. The second iterator to tile
        # 3. The third iterator to tile
        # 4. The tile size for the first iterator
        # 5. The tile size for the second iterator
        # 6. The tile size for the third iterator

        assert len(params) == 6
        assert (
            isinstance(params[0], tuple)
            and isinstance(params[1], tuple)
            and isinstance(params[2], tuple)
        )
        assert (
            isinstance(params[3], int)
            and isinstance(params[4], int)
            and isinstance(params[5], int)
        )

        self.params = params
        self.comps = comps

        self.iterators = [params[0], params[1], params[2]]
        self.tile_sizes = [params[3], params[4], params[5]]

        super().__init__(type=TiramisuActionType.TILING_3D, params=params, comps=comps)

    def initialize_action_for_tree(self, tiramisu_tree: TiramisuTree):
        # clone the tree to be able to restore it later
        self.tree = copy.deepcopy(tiramisu_tree)
        for idx, iterator in enumerate(self.iterators):
            if iterator not in tiramisu_tree.iterators:
                self.iterators[idx] = self.tree.get_iterator_of_computation(
                    *iterator
                ).id

        if self.comps is None:
            outermost_iterator_id = self.iterators[0]
            for iterator in self.iterators[1:]:
                if iterator[1] < outermost_iterator_id[1]:
                    outermost_iterator_id = iterator

            outermost_iterator = self.tree.iterators[outermost_iterator_id]
            # get the computations of the outermost iterator to tile
            # which include the computations of the other iterators
            self.comps = self.tree.get_iterator_subtree_computations(
                outermost_iterator.id
            )

            # sort the computations according to the absolute order
            self.comps.sort(
                key=lambda comp: self.tree.computations_absolute_order[comp]
            )

        self.set_string_representations(tiramisu_tree)

    def set_string_representations(self, tiramisu_tree: TiramisuTree):
        assert len(self.params) == 6
        assert self.iterators is not None
        assert self.comps is not None

        all_comps = tiramisu_tree.computations

        if len(all_comps) > 1:
            all_comps.sort(
                key=lambda comp: tiramisu_tree.computations_absolute_order[comp]
            )
            fusion_levels = self.get_fusion_levels(all_comps, tiramisu_tree)

        self.tiramisu_optim_str = ""
        loop_levels_and_factors = [
            str(self.iterators[0][1]),
            str(self.iterators[1][1]),
            str(self.iterators[2][1]),
            str(self.tile_sizes[0]),
            str(self.tile_sizes[1]),
            str(self.tile_sizes[2]),
        ]
        for comp in self.comps:
            self.tiramisu_optim_str += (
                f"{comp}.tile({', '.join(loop_levels_and_factors)});\n"
            )
        if len(all_comps) > 1:
            self.tiramisu_optim_str += f"clear_implicit_function_sched_graph();\n    {all_comps[0]}{''.join([f'.then({comp},{fusion_level})' for comp, fusion_level in zip(all_comps[1:], fusion_levels)])};\n"  # noqa: E501

        self.str_representation = "T3(L{},L{},L{},{},{},{},comps={})".format(
            *loop_levels_and_factors, self.comps
        )

        self.legality_check_string = self.tiramisu_optim_str

    @classmethod
    def get_candidates(
        cls, program_tree: TiramisuTree
    ) -> Dict[str, List[Tuple[str, str, str]]]:
        candidates: Dict[str, List[Tuple[str, str, str]]] = {}

        candidate_sections = program_tree.get_candidate_sections()

        for root_id in candidate_sections:
            candidates[root_id] = []
            for section in candidate_sections[root_id]:
                # Only consider sections with more than two iterators
                if len(section) > 2:
                    # Get all possible combinations of 3 successive iterators
                    successive_3_iterators = [
                        (
                            section[i],
                            section[i + 1],
                            section[i + 2],
                        )
                        for i in range(len(section) - 2)
                    ]
                    candidates[root_id].extend(successive_3_iterators)

        return candidates

    def get_fusion_levels(
        self,
        ordered_computations: List[str],
        tiramisu_tree: TiramisuTree,
    ):
        fusion_levels: List[int] = []
        # for every pair of successive computations
        # get the shared iterator level
        for comp1, comp2 in itertools.pairwise(ordered_computations):
            # get the shared iterator level
            iter_comp_1 = tiramisu_tree.get_iterator_of_computation(comp1)
            iter_comp_2 = tiramisu_tree.get_iterator_of_computation(comp2)
            fusion_level: int | None = None

            # get the shared iterator level
            while iter_comp_1.name != iter_comp_2.name:
                if iter_comp_1.level > iter_comp_2.level:
                    # if parent is None then
                    # the iterators don't have a common parent
                    if iter_comp_1.parent_iterator is None:
                        fusion_level = -1
                        break
                    else:
                        iter_comp_1 = tiramisu_tree.iterators[
                            iter_comp_1.parent_iterator
                        ]
                else:
                    if iter_comp_2.parent_iterator is None:
                        fusion_level = -1
                        break
                    else:
                        iter_comp_2 = tiramisu_tree.iterators[
                            iter_comp_2.parent_iterator
                        ]

            # same iterator
            if fusion_level is None:
                fusion_level = iter_comp_1.level

            if comp1 in self.comps and comp2 in self.comps:
                fusion_level += 3

            fusion_levels.append(fusion_level)

        return fusion_levels
