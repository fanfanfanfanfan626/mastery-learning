#!/usr/bin/env python3
"""Validate the machine-readable teaching boundary before classroom rendering."""

from __future__ import annotations

from typing import Any


MENTAL_MOVES = {"notice", "predict", "classify", "trace", "choose", "repair", "explain"}
FIELDS = {
    "schema_version",
    "learner_problem",
    "current_target",
    "mental_move",
    "new_terms",
    "answer_options",
    "concrete_experience",
    "example",
    "counterexample",
    "visual",
    "action",
    "evidence_boundary",
    "feedback_plan",
}
OPTIONAL_FIELDS = {"learner_promise"}


class TeachingTurnError(ValueError):
    pass


def _text(value: Any, field: str, maximum: int = 2_000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TeachingTurnError(f"teaching_turn.{field} must be non-empty text")
    result = value.strip()
    if len(result) > maximum:
        raise TeachingTurnError(f"teaching_turn.{field} must be at most {maximum} characters")
    return result


def _exact_object(
    value: Any, field: str, fields: set[str], optional_fields: set[str] | None = None
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TeachingTurnError(f"teaching_turn.{field} must be an object")
    missing = sorted(fields - set(value))
    optional_fields = optional_fields or set()
    unknown = sorted(set(value) - fields - optional_fields)
    if missing or unknown:
        raise TeachingTurnError(
            f"teaching_turn.{field} fields are invalid; missing={missing}, unknown={unknown}"
        )
    return value


def _case(value: Any, field: str) -> dict[str, str]:
    item = _exact_object(value, field, {"case", "deciding_feature"})
    return {
        "case": _text(item["case"], f"{field}.case"),
        "deciding_feature": _text(item["deciding_feature"], f"{field}.deciding_feature", 400),
    }


def validate_teaching_turn(value: Any, action_prompt: str) -> dict[str, Any]:
    turn = _exact_object(value, "root", FIELDS, OPTIONAL_FIELDS)
    if turn.get("schema_version") != 1:
        raise TeachingTurnError("teaching_turn.schema_version must equal 1")

    mental_move = _text(turn.get("mental_move"), "mental_move", 40)
    if mental_move not in MENTAL_MOVES:
        raise TeachingTurnError(f"teaching_turn.mental_move must be one of {sorted(MENTAL_MOVES)}")

    terms = turn.get("new_terms")
    if not isinstance(terms, list) or len(terms) > 3:
        raise TeachingTurnError("teaching_turn.new_terms must contain 0..3 term objects")
    normalized_terms: list[dict[str, str]] = []
    seen_terms: set[str] = set()
    for index, raw in enumerate(terms):
        item = _exact_object(raw, f"new_terms[{index}]", {"term", "meaning"})
        term = _text(item["term"], f"new_terms[{index}].term", 120)
        key = term.casefold()
        if key in seen_terms:
            raise TeachingTurnError("teaching_turn.new_terms must be unique")
        seen_terms.add(key)
        normalized_terms.append({
            "term": term,
            "meaning": _text(item["meaning"], f"new_terms[{index}].meaning", 400),
        })

    answer_options = turn.get("answer_options")
    if not isinstance(answer_options, list) or len(answer_options) > 8:
        raise TeachingTurnError("teaching_turn.answer_options must contain 0..8 text items")
    normalized_options = [
        _text(item, f"answer_options[{index}]", 200)
        for index, item in enumerate(answer_options)
    ]
    if len({item.casefold() for item in normalized_options}) != len(normalized_options):
        raise TeachingTurnError("teaching_turn.answer_options must be unique")

    example = _case(turn.get("example"), "example")
    counterexample = _case(turn.get("counterexample"), "counterexample")
    visual_raw = _exact_object(turn.get("visual"), "visual", {"form", "deciding_feature"})
    visual = {
        "form": _text(visual_raw["form"], "visual.form"),
        "deciding_feature": _text(visual_raw["deciding_feature"], "visual.deciding_feature", 400),
    }
    deciding_features = {
        example["deciding_feature"].casefold(),
        counterexample["deciding_feature"].casefold(),
        visual["deciding_feature"].casefold(),
    }
    if len(deciding_features) != 1:
        raise TeachingTurnError(
            "teaching_turn example, counterexample, and visual must share one deciding_feature"
        )

    action = _text(turn.get("action"), "action")
    if action != action_prompt.strip():
        raise TeachingTurnError("teaching_turn.action must exactly match action.prompt")

    evidence_raw = _exact_object(
        turn.get("evidence_boundary"), "evidence_boundary", {"can_show", "not_observed"}
    )
    not_observed = evidence_raw.get("not_observed")
    if not isinstance(not_observed, list) or not 1 <= len(not_observed) <= 8:
        raise TeachingTurnError("teaching_turn.evidence_boundary.not_observed must contain 1..8 items")
    feedback_raw = _exact_object(
        turn.get("feedback_plan"), "feedback_plan", {"earliest_error", "first_hint", "retry_shape"}
    )

    learner_problem = _text(turn.get("learner_problem"), "learner_problem")
    learner_promise = _text(turn.get("learner_promise", learner_problem), "learner_promise", 240)

    return {
        "schema_version": 1,
        "learner_problem": learner_problem,
        "learner_promise": learner_promise,
        "current_target": _text(turn.get("current_target"), "current_target"),
        "mental_move": mental_move,
        "new_terms": normalized_terms,
        "answer_options": normalized_options,
        "concrete_experience": _text(turn.get("concrete_experience"), "concrete_experience"),
        "example": example,
        "counterexample": counterexample,
        "visual": visual,
        "action": action,
        "evidence_boundary": {
            "can_show": _text(evidence_raw.get("can_show"), "evidence_boundary.can_show"),
            "not_observed": [
                _text(item, f"evidence_boundary.not_observed[{index}]", 400)
                for index, item in enumerate(not_observed)
            ],
        },
        "feedback_plan": {
            "earliest_error": _text(feedback_raw.get("earliest_error"), "feedback_plan.earliest_error"),
            "first_hint": _text(feedback_raw.get("first_hint"), "feedback_plan.first_hint"),
            "retry_shape": _text(feedback_raw.get("retry_shape"), "feedback_plan.retry_shape"),
        },
    }
