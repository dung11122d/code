from __future__ import annotations

from abc import ABC, abstractmethod

from schemas import Segment


class Translator(ABC):
    @abstractmethod
    def translate_segments(self, segments: list[Segment]) -> list[Segment]:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError
