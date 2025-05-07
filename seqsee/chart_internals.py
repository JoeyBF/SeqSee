import pydantic
from typing import Dict, Iterator, List, Literal, Optional, Union, Any


class DimensionRange(pydantic.BaseModel):
    min: Optional[int] = None
    max: Optional[int] = None


class Point(pydantic.BaseModel):
    x: float
    y: float


class Attribute(pydantic.BaseModel):
    color: Optional[str] = None
    size: Optional[float] = None
    thickness: Optional[float] = None
    arrowTip: Optional[Literal["simple", "none"]] = None
    pattern: Optional[Literal["solid", "dashed", "dotted"]] = None

    # For additional string properties
    model_config = pydantic.ConfigDict(extra="allow")
    __pydantic_extra__: Dict[str, str] = {}

    def items(self) -> Iterator[tuple[str, Union[str, float]]]:
        def inner_items() -> Iterator[tuple[str, Union[str, float]]]:
            if self.color:
                yield ("color", self.color)
            if self.size:
                yield ("size", self.size)
            if self.thickness:
                yield ("thickness", self.thickness)
            if self.arrowTip:
                yield ("arrowTip", self.arrowTip)
            if self.pattern:
                yield ("pattern", self.pattern)
            for key, value in self.__pydantic_extra__.items():
                yield (key, value)

        for key, value in inner_items():
            if value is not None:
                yield (key, value)


class ChartMetadata(pydantic.BaseModel):
    htmltitle: str = ""
    title: str = ""
    displaytitle: str = ""


class ChartConfig(pydantic.BaseModel):
    width: DimensionRange = DimensionRange()
    height: DimensionRange = DimensionRange()
    scale: float = 60.0
    nodeSize: float = 0.04
    nodeSpacing: float = 0.02
    nodeSlope: Optional[float] = 0.0

    model_config = pydantic.ConfigDict(extra="forbid")


Attributes = List[Union[str, Attribute]]


class GlobalAttributes(pydantic.BaseModel):
    grid: Attributes = [Attribute(color="#ccc", thickness=0.01)]
    defaultNode: Attributes = [Attribute(color="black")]
    defaultEdge: Attributes = [Attribute(color="black", thickness=0.02)]

    model_config = pydantic.ConfigDict(extra="allow")
    __pydantic_extra__: Dict[str, Attributes] = {}

    def items(self) -> Iterator[tuple[str, Attributes]]:
        yield ("grid", self.grid)
        yield ("defaultNode", self.defaultNode)
        yield ("defaultEdge", self.defaultEdge)
        for key, value in self.__pydantic_extra__.items():
            yield (key, value)

    def merge_with_defaults(self):
        defaults = GlobalAttributes()
        current = self.model_dump()
        for key, value in defaults.items():
            # This creates a new list instead of modifying the existing one, which would be bad.
            # This is because it could mutate a default value, which would ultimately corrupt every
            # other chart.
            current[key] = value + current[key]
        return GlobalAttributes(**current)


class Colors(pydantic.BaseModel):
    backgroundColor: str = "white"
    borderColor: str = "black"
    textColor: str = "black"

    model_config = pydantic.ConfigDict(extra="allow")
    __pydantic_extra__: Dict[str, str] = {}


class Aliases(pydantic.BaseModel):
    colors: Colors = Colors()
    attributes: GlobalAttributes = GlobalAttributes()

    model_config = pydantic.ConfigDict(extra="forbid")


class Header(pydantic.BaseModel):
    metadata: ChartMetadata = ChartMetadata()
    chart: ChartConfig = ChartConfig()
    aliases: Aliases = Aliases()

    model_config = pydantic.ConfigDict(extra="forbid")


class Node(pydantic.BaseModel):
    x: int
    y: int
    position: int = 0
    label: str = ""
    attributes: Attributes = []

    _absoluteX: Optional[float] = None
    _absoluteY: Optional[float] = None

    model_config = pydantic.ConfigDict(extra="forbid")


class Edge(pydantic.BaseModel):
    source: str
    target: Optional[str] = None
    offset: Optional[Point] = None
    label: str = ""
    bezier: Optional[List[Point]] = None
    attributes: Attributes = []

    model_config = pydantic.ConfigDict(
        extra="forbid",
        json_schema_extra={
            "oneOf": [{"required": ["target"]}, {"required": ["offset"]}]
        },
    )
