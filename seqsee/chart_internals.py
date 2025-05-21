import pydantic
from typing import Dict, Iterator, List, Literal, Optional, Union, Any


class DimensionRange(pydantic.BaseModel):
    min: Optional[int] = None
    max: Optional[int] = None

    def __contains__(self, item: int) -> bool:
        if self.min is not None and item < self.min:
            return False
        if self.max is not None and item > self.max:
            return False
        return True

    def make_even(self):
        if self.min is not None and self.min % 2 != 0:
            self.min -= 1
        if self.max is not None and self.max % 2 != 0:
            self.max += 1


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
            if self.color is not None:
                yield ("color", self.color)
            if self.size is not None:
                yield ("size", self.size)
            if self.thickness is not None:
                yield ("thickness", self.thickness)
            if self.arrowTip is not None:
                yield ("arrowTip", self.arrowTip)
            if self.pattern is not None:
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
    id: int = 0


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

    def svg(self, scale: float) -> str:
        from seqsee.main import style_and_aliases_from_attributes

        assert self._absoluteX is not None
        assert self._absoluteY is not None

        cx = self._absoluteX * scale
        cy = self._absoluteY * scale

        style, aliases = style_and_aliases_from_attributes(self.attributes)
        style = style.generate(indent=0).replace("\n", " ").strip(" {}")
        if style:
            style = f' style="{style}"'
        aliases = " ".join(aliases)

        label = self.label

        return f'<circle class="defaultNode {aliases}" cx="{cx}" cy="{cy}"{style} data-label="{label}"></circle>'


class Edge(pydantic.BaseModel):
    source: str
    target: Optional[str] = None
    offset: Optional[Point] = None
    label: str = ""
    bezier: Optional[List[Point]] = None
    attributes: Attributes = []

    _concrete_source: Optional[Node] = None
    _concrete_target: Optional[Node] = None

    model_config = pydantic.ConfigDict(
        extra="forbid",
        json_schema_extra={
            "oneOf": [{"required": ["target"]}, {"required": ["offset"]}]
        },
    )

    def svg(self, scale: float) -> str:
        from seqsee.main import style_and_aliases_from_attributes

        assert self._concrete_source is not None
        source = self._concrete_source
        assert source._absoluteX is not None
        assert source._absoluteY is not None

        if self.target is not None:
            assert self._concrete_target is not None
            target = self._concrete_target
            assert target._absoluteX is not None
            assert target._absoluteY is not None

            target_x = target._absoluteX * scale
            target_y = target._absoluteY * scale
        elif self.offset is not None:
            target_x = (source._absoluteX + self.offset.x) * scale
            target_y = (source._absoluteY + self.offset.y) * scale
        else:
            # Impossible due to schema
            raise NotImplementedError

        x1 = source._absoluteX * scale
        y1 = source._absoluteY * scale

        attributes = self.attributes
        style, aliases = style_and_aliases_from_attributes(attributes)
        style = style.generate(indent=0).replace("\n", " ").strip(" {}")
        aliases = " ".join(aliases)

        if self.bezier is not None:
            control_points = self.bezier
            if len(control_points) == 1:
                control_x = control_points[0].x * scale + x1
                control_y = control_points[0].y * scale + y1
                curve_d = f"Q {control_x} {control_y} {target_x} {target_y}"
            elif len(control_points) == 2:
                control0_x = control_points[0].x * scale + x1
                control0_y = control_points[0].y * scale + y1
                control1_x = control_points[1].x * scale + target_x
                control1_y = control_points[1].y * scale + target_y
                curve_d = f"C {control0_x} {control0_y} {control1_x} {control1_y} {target_x} {target_y}"
            else:
                # Impossible due to schema
                raise NotImplementedError
            edge_svg = f'<path d="M {x1} {y1} {curve_d}" class="{aliases}" style="fill: none;{style}"></path>'
        else:
            if style:
                style = f' style="{style}"'
            edge_svg = f'<line x1="{x1}" y1="{y1}" x2="{target_x}" y2="{target_y}" class="defaultEdge {aliases}"{style}></line>'

        return edge_svg
