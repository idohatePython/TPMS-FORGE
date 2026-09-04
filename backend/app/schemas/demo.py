from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

TpmsType = Literal["gyroid", "schwarz_p", "diamond", "iwp", "neovius", "lidinoid"]


class DemoTpmsRequest(BaseModel):
    tpms_type: TpmsType
    cell_size: float = Field(ge=2, le=30)
    cell_count: int = Field(ge=1, le=3)
    wall_thickness_mm: float = Field(ge=0.2, le=4)
    quality: Literal["fast", "standard"] = "fast"
    gradient_axis: Literal["x", "y", "z"] = "x"
    gradient_start_offset: float = Field(default=-0.35, ge=-1.5, le=1.5)
    gradient_end_offset: float = Field(default=0.35, ge=-1.5, le=1.5)

    @model_validator(mode="after")
    def validate_wall_thickness(self) -> DemoTpmsRequest:
        if self.wall_thickness_mm >= self.cell_size / 2:
            raise ValueError("wall thickness must be less than half the cell size")
        return self
