import re

from pydantic import BaseModel, ValidationInfo, field_validator

COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
LABEL_MAX_LEN = 200
ALIGNMENT_MINUTES = {0, 15, 30, 45}


def _validate_hhmm(value: str) -> str:
    if len(value) != 16 or value[10] != "T":
        raise ValueError("must be ISO 8601 local datetime: YYYY-MM-DDTHH:MM")
    hhmm = value[11:]
    hh, mm = hhmm.split(":")
    if not (hh.isdigit() and mm.isdigit() and 0 <= int(hh) <= 23 and int(mm) <= 59):
        raise ValueError(f"invalid time of day: {hhmm}")
    if int(mm) not in ALIGNMENT_MINUTES:
        raise ValueError(f"minutes must be one of 00/15/30/45, got :{mm}")
    return value


class BlockIn(BaseModel):
    start: str
    end: str
    label: str = ""
    color: str = "#4a90d9"

    @field_validator("start", "end")
    @classmethod
    def valid_hhmm(cls, value: str) -> str:
        return _validate_hhmm(value)

    @field_validator("end")
    @classmethod
    def end_after_start(cls, end: str, info: ValidationInfo) -> str:
        start = info.data.get("start")
        if start is not None and end <= start:
            raise ValueError("end must be after start")
        return end

    @field_validator("label")
    @classmethod
    def label_not_too_long(cls, value: str) -> str:
        if len(value) > LABEL_MAX_LEN:
            raise ValueError(f"label must be at most {LABEL_MAX_LEN} characters")
        return value

    @field_validator("color")
    @classmethod
    def color_is_hex(cls, value: str) -> str:
        if not COLOR_RE.match(value):
            raise ValueError("color must match #RRGGBB")
        return value


class BlockPatch(BaseModel):
    start: str | None = None
    end: str | None = None
    label: str | None = None
    color: str | None = None

    @field_validator("start", "end")
    @classmethod
    def valid_hhmm(cls, value: str | None) -> str | None:
        if value is not None:
            return _validate_hhmm(value)
        return value

    @field_validator("label")
    @classmethod
    def label_not_too_long(cls, value: str | None) -> str | None:
        if value is not None and len(value) > LABEL_MAX_LEN:
            raise ValueError(f"label must be at most {LABEL_MAX_LEN} characters")
        return value

    @field_validator("color")
    @classmethod
    def color_is_hex(cls, value: str | None) -> str | None:
        if value is not None and not COLOR_RE.match(value):
            raise ValueError("color must match #RRGGBB")
        return value


class BlockOut(BaseModel):
    id: int
    start: str
    end: str
    label: str
    color: str
    source: str
