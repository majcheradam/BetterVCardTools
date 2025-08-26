from __future__ import annotations

from typing import NotRequired, TypedDict


class NameStruct(TypedDict, total=False):
    family: str
    given: str
    additional: str
    prefix: str
    suffix: str


class EmailEntry(TypedDict):
    value: str
    types: list[str]


class PhoneEntry(TypedDict):
    value: str
    types: list[str]


class Contact(TypedDict, total=False):
    name: str | None
    n: NameStruct | None
    emails: list[EmailEntry]
    phones: list[PhoneEntry]
    org: NotRequired[list[str] | None]
    bday: NotRequired[str | None]
    notes: NotRequired[list[str] | None]


__all__ = [
    "NameStruct",
    "EmailEntry",
    "PhoneEntry",
    "Contact",
]
