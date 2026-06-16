from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Literal


AnswerSource = Literal["官方答案", "推导答案", "待核对"]


@dataclass(frozen=True)
class SourcePage:
    file: str
    page: int
    image_path: str


@dataclass(frozen=True)
class KnowledgePoint:
    id: str
    chapter: str
    title: str
    summary: str
    must_know: str
    intuition: str
    prerequisites: list[str]
    formulas: list[str]
    source_pages: list[SourcePage]
    related_questions: list[str]
    pitfalls: list[str]


@dataclass(frozen=True)
class SubQuestion:
    id: str
    prompt: str
    answer: str
    solution_steps: list[str]


@dataclass(frozen=True)
class Question:
    id: str
    chapter: str
    title: str
    prompt: str
    image_paths: list[str]
    knowledge_ids: list[str]
    source_pages: list[SourcePage]
    subquestions: list[SubQuestion]
    answer_source: AnswerSource
    official_answer_pages: list[SourcePage] = field(default_factory=list)


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    return value
