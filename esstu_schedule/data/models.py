"""Validated boundary models. Extra source/provenance fields are preserved."""

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FetchedPage:
    html: str
    last_modified: str | None
    source_mode: str
    checked_at: str | None
    source_sha256: str | None = None


@dataclass(frozen=True)
class Lesson:
    subject: str

    @classmethod
    def from_payload(cls, data):
        if not isinstance(data, dict) or not isinstance(data.get("subject"), str):
            raise ValueError("Invalid lesson")
        return cls(data["subject"])


@dataclass(frozen=True)
class Pair:
    number: int
    start: str
    end: str
    lessons: list[dict[str, Any]]

    @classmethod
    def from_payload(cls, data):
        number = data["number"]
        if not isinstance(number, int) or not 1 <= number <= 12:
            raise ValueError("Invalid pair number")
        for time in (data["start"], data["end"]):
            if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", time):
                raise ValueError("Invalid pair time")
        if data["start"] >= data["end"] or not isinstance(data["lessons"], list):
            raise ValueError("Invalid pair interval or lessons")
        for lesson in data["lessons"]:
            Lesson.from_payload(lesson)
        return cls(number, data["start"], data["end"], data["lessons"])


@dataclass(frozen=True)
class Schedule:
    weeks: dict
    is_incomplete: bool = False
    parse_errors: list[str] = field(default_factory=list)

    @classmethod
    def from_payload(cls, data):
        weeks = data.get("weeks")
        if not isinstance(weeks, dict) or set(weeks) - {"1", "2"}:
            raise ValueError("Invalid schedule weeks")
        for days in weeks.values():
            if not isinstance(days, dict):
                raise ValueError("Invalid schedule days")
            for day in days.values():
                if not isinstance(day.get("pairs"), list):
                    raise ValueError("Invalid day pairs")
                for pair in day["pairs"]:
                    Pair.from_payload(pair)
        return cls(weeks, bool(data.get("is_incomplete")), data.get("parse_errors", []))


def validate_schedule(payload):
    Schedule.from_payload(payload)
    return payload
