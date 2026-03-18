from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class TaxonomyMainCategory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    subcategories: list[str] = Field(default_factory=list)


class TaxonomyMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")

    main_category: str
    subcategory: str


class ClassificationTaxonomyFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    main_categories: list[TaxonomyMainCategory] = Field(default_factory=list)
    internal_category_mappings: dict[str, TaxonomyMapping] = Field(default_factory=dict)


class ClassificationTaxonomy:
    def __init__(self, payload: ClassificationTaxonomyFile) -> None:
        self._payload = payload

    @classmethod
    def from_file(cls, path: str | Path) -> "ClassificationTaxonomy":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(ClassificationTaxonomyFile.model_validate(payload))

    def prompt_text(self) -> str:
        lines = [
            "Use this classification taxonomy.",
            "Return main_category as one of the listed main categories.",
            "Return subcategory as one of the listed subcategories under that main category.",
            "Return category as a short internal snake_case label.",
        ]
        for entry in self._payload.main_categories:
            subcategories = ", ".join(entry.subcategories)
            lines.append(f"- {entry.name}: {subcategories}")
        return "\n".join(lines)

    def resolve(
        self,
        *,
        category: str,
        main_category: str | None = None,
        subcategory: str | None = None,
    ) -> tuple[str | None, str | None]:
        if main_category and subcategory and self.is_valid(main_category, subcategory):
            return main_category, subcategory

        mapped = self._payload.internal_category_mappings.get(category)
        if mapped:
            return mapped.main_category, mapped.subcategory

        return main_category, subcategory

    def is_valid(self, main_category: str, subcategory: str) -> bool:
        for entry in self._payload.main_categories:
            if entry.name == main_category and subcategory in entry.subcategories:
                return True
        return False


@lru_cache(maxsize=4)
def load_classification_taxonomy(path: str | Path) -> ClassificationTaxonomy:
    return ClassificationTaxonomy.from_file(path)
