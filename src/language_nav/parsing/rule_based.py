from __future__ import annotations

import re
from collections.abc import Iterable

from language_nav.models import (
    Clause,
    ClauseType,
    InstructionHypotheses,
    ParseAlternative,
)


class RuleBasedParser:
    """Small Protocol 1.0 grammar with explicit, serializable alternatives."""

    VERSION = "rule-v0.1.0"
    COLORS = "red|blue|green|yellow|black|white"
    ORDINALS = {"first": 1, "second": 2, "third": 3}

    def parse(
        self,
        text: str,
        instruction_id: str,
        provenance: str = "hand_authored",
    ) -> InstructionHypotheses:
        if not text.strip():
            raise ValueError("instruction text must not be empty")
        parts = self._split_clauses(text)
        clauses = tuple(self._parse_clause(part, i) for i, part in enumerate(parts))
        return InstructionHypotheses(
            instruction_id=instruction_id,
            raw_text=text.strip(),
            parser_version=self.VERSION,
            clauses=clauses,
            provenance=provenance,
        )

    @staticmethod
    def _split_clauses(text: str) -> list[str]:
        normalized = re.sub(r"\s+", " ", text.strip().rstrip("."))
        parts = re.split(r"\s*(?:,|\band\s+then\b|\bthen\b)\s*", normalized, flags=re.I)
        return [part.strip() for part in parts if part.strip()]

    def _parse_clause(self, text: str, index: int) -> Clause:
        lower = text.lower()
        clause_id = f"c{index:02d}"
        strength = 0.55 if re.search(r"\bmay\b", lower) else 0.50 if re.search(r"\bmight\b", lower) else 0.85

        terminal = re.search(r"\bstop\s+(?:near|beside|at)\s+(?:the\s+)?(.+)$", lower)
        if terminal:
            relation = "near" if "near" in lower or "at" in lower else "beside"
            target, attrs = self._entity_phrase(terminal.group(1))
            return self._clause(clause_id, text, ClauseType.TERMINAL, "stop", target, relation, attrs, strength)

        topology = re.search(
            r"\b(?:take|use)\s+the\s+(first|second|third)\s+(doorway|door|junction)\s+on\s+the\s+(left|right)",
            lower,
        )
        if topology:
            alt = ParseAlternative(
                probability=1.0,
                action="take_branch",
                target=topology.group(2),
                relation="branch",
                branch_index=self.ORDINALS[topology.group(1)],
                side=topology.group(3),
                epistemic_strength=strength,
            )
            return Clause(clause_id, text, ClauseType.TOPOLOGY, (alt,))

        turn = re.search(r"\bturn\s+(left|right)\s+(before|after)\s+(?:the\s+)?(.+)$", lower)
        if turn:
            target, attrs = self._entity_phrase(turn.group(3))
            return self._clause(
                clause_id,
                text,
                ClauseType.TURN,
                f"turn_{turn.group(1)}",
                target,
                turn.group(2),
                attrs,
                strength,
            )

        landmark = re.search(r"\b(?:continue|go|walk|move)\s+(past|near|beside)\s+(?:the\s+)?(.+)$", lower)
        if landmark:
            target, attrs = self._entity_phrase(landmark.group(2))
            return self._clause(
                clause_id, text, ClauseType.LANDMARK, "continue", target, landmark.group(1), attrs, strength
            )

        motion = re.search(r"\b(?:go|continue|walk|move)\s+(?:through|along|down)\s+(?:the\s+)?(.+)$", lower)
        if motion:
            target, attrs = self._entity_phrase(motion.group(1))
            return self._clause(clause_id, text, ClauseType.MOTION, "traverse", target, None, attrs, strength)

        raise ValueError(f"unsupported Protocol 1.0 clause: {text!r}")

    def _entity_phrase(self, phrase: str) -> tuple[str, dict[str, str]]:
        words = phrase.strip().replace(" ", "_").split("_")
        attrs: dict[str, str] = {}
        if words and re.fullmatch(self.COLORS, words[0]):
            attrs["color"] = words.pop(0)
        return "_".join(words), attrs

    @staticmethod
    def _clause(
        clause_id: str,
        text: str,
        clause_type: ClauseType,
        action: str,
        target: str,
        relation: str | None,
        attributes: dict[str, str],
        strength: float,
    ) -> Clause:
        alternatives: Iterable[ParseAlternative]
        if target in {"door", "doorway", "entrance"}:
            alternatives = (
                ParseAlternative(0.7, action, target, relation, attributes, epistemic_strength=strength),
                ParseAlternative(0.3, action, "doorway", relation, attributes, epistemic_strength=strength),
            )
        else:
            alternatives = (ParseAlternative(1.0, action, target, relation, attributes, epistemic_strength=strength),)
        return Clause(clause_id, text, clause_type, tuple(alternatives))
