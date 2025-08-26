from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Name:
    family: str = ""
    given: str = ""
    additional: str = ""
    prefix: str = ""
    suffix: str = ""


@dataclass
class Email:
    value: str
    types: List[str] = field(default_factory=list)


@dataclass
class Phone:
    value: str
    types: List[str] = field(default_factory=list)


@dataclass
class Contact:
    name: Optional[str]
    n: Optional[Name]
    emails: List[Email] = field(default_factory=list)
    phones: List[Phone] = field(default_factory=list)
    org: Optional[List[str]] = None
