from __future__ import annotations

from typing import List, NotRequired, Optional, TypedDict


class NameStruct(TypedDict, total=False):
    family: str
    given: str
    additional: str
    prefix: str
    suffix: str


class EmailEntry(TypedDict):
    value: str
    types: List[str]


class PhoneEntry(TypedDict):
    value: str
    types: List[str]


class Contact(TypedDict, total=False):
    name: Optional[str]
    n: Optional[NameStruct]
    emails: List[EmailEntry]
    phones: List[PhoneEntry]
    org: NotRequired[Optional[List[str]]]
    bday: NotRequired[Optional[str]]
    notes: NotRequired[Optional[List[str]]]


__all__ = [
    "NameStruct",
    "EmailEntry",
    "PhoneEntry",
    "Contact",
]
