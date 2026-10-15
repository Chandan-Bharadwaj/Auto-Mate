"""PythonOCC topology and XCAF assembly navigation utilities.

These functions provide Open CASCADE Technology (OCCT) topological decomposition
and assembly tree extraction. OCC imports are guarded/lazy so that importing
this module in environments without PythonOCC does not raise an ImportError.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


def is_occ_available() -> bool:
    """Check if OCC.Core modules can be imported in the current Python runtime."""
    try:
        import OCC.Core.TopoDS  # noqa: F401
        import OCC.Core.TopExp  # noqa: F401
        import OCC.Core.TopAbs  # noqa: F401
        return True
    except (ImportError, AttributeError):
        return False


def explore_solids(occ_shape: Any) -> list[Any]:
    """Extract TopoDS_Solid bodies from an Open CASCADE TopoDS_Shape using TopExp_Explorer."""
    try:
        from OCC.Core.TopAbs import TopAbs_SOLID
        from OCC.Core.TopExp import TopExp_Explorer
        from OCC.Core.TopoDS import topods
    except ImportError as exc:
        raise RuntimeError(
            "PythonOCC (OCC.Core) is not available in the current environment"
        ) from exc

    explorer = TopExp_Explorer(occ_shape, TopAbs_SOLID)
    solids: list[Any] = []
    while explorer.More():
        solids.append(topods.Solid(explorer.Current()))
        explorer.Next()
    return solids


def explore_faces(occ_shape: Any) -> list[Any]:
    """Extract TopoDS_Face instances from an Open CASCADE TopoDS_Shape using TopExp_Explorer."""
    try:
        from OCC.Core.TopAbs import TopAbs_FACE
        from OCC.Core.TopExp import TopExp_Explorer
        from OCC.Core.TopoDS import topods
    except ImportError as exc:
        raise RuntimeError(
            "PythonOCC (OCC.Core) is not available in the current environment"
        ) from exc

    explorer = TopExp_Explorer(occ_shape, TopAbs_FACE)
    faces: list[Any] = []
    while explorer.More():
        faces.append(topods.Face(explorer.Current()))
        explorer.Next()
    return faces


def get_surface_type(occ_face: Any) -> str:
    """Return the surface geometry type name (e.g. 'Plane', 'Cylinder', 'Cone', 'Sphere', 'Torus', 'BSpline')."""
    try:
        from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
        from OCC.Core.GeomAbs import (
            GeomAbs_BezierSurface,
            GeomAbs_BSplineSurface,
            GeomAbs_Cone,
            GeomAbs_Cylinder,
            GeomAbs_OffsetSurface,
            GeomAbs_OtherSurface,
            GeomAbs_Plane,
            GeomAbs_Sphere,
            GeomAbs_SurfaceOfExtrusion,
            GeomAbs_SurfaceOfRevolution,
            GeomAbs_Torus,
        )
    except ImportError as exc:
        raise RuntimeError(
            "PythonOCC (OCC.Core) is not available in the current environment"
        ) from exc

    adaptor = BRepAdaptor_Surface(occ_face)
    st = adaptor.GetType()
    mapping = {
        GeomAbs_Plane: "Plane",
        GeomAbs_Cylinder: "Cylinder",
        GeomAbs_Cone: "Cone",
        GeomAbs_Sphere: "Sphere",
        GeomAbs_Torus: "Torus",
        GeomAbs_BezierSurface: "BezierSurface",
        GeomAbs_BSplineSurface: "BSplineSurface",
        GeomAbs_SurfaceOfRevolution: "SurfaceOfRevolution",
        GeomAbs_SurfaceOfExtrusion: "SurfaceOfExtrusion",
        GeomAbs_OffsetSurface: "OffsetSurface",
        GeomAbs_OtherSurface: "OtherSurface",
    }
    return mapping.get(st, "Unknown")


@dataclass(frozen=True, slots=True)
class XCAFComponent:
    label_entry: str
    name: str
    is_assembly: bool
    shape: Any
    children: tuple[XCAFComponent, ...] = ()


def read_xcaf_assembly_tree(step_filepath: str | Path) -> list[XCAFComponent]:
    """Read a STEP file using STEPCAFControl_Reader and return its assembly tree structure."""
    try:
        from OCC.Core.IFSelect import IFSelect_RetDone
        from OCC.Core.STEPCAFControl import STEPCAFControl_Reader
        from OCC.Core.TDF import TDF_Label, TDF_LabelSequence, TDF_Tool
        from OCC.Core.TDataStd import TDataStd_Name
        from OCC.Core.TDocStd import TDocStd_Document
        from OCC.Core.XCAFApp import XCAFApp_Application
        from OCC.Core.XCAFDoc import XCAFDoc_DocumentTool
    except ImportError as exc:
        raise RuntimeError(
            "PythonOCC (OCC.Core) is not available in the current environment"
        ) from exc

    filepath_str = str(step_filepath)
    app = XCAFApp_Application.GetApplication()
    doc = TDocStd_Document("MDTV-XCAF")
    app.InitDocument(doc)

    reader = STEPCAFControl_Reader()
    reader.SetColorMode(True)
    reader.SetNameMode(True)
    reader.SetLayerMode(True)

    status = reader.ReadFile(filepath_str)
    if status != IFSelect_RetDone:
        raise ValueError(f"Failed to read STEP file: {filepath_str}")

    if not reader.Transfer(doc):
        raise RuntimeError(f"Failed to transfer STEP file contents into XDE document: {filepath_str}")

    shape_tool = XCAFDoc_DocumentTool.ShapeTool(doc.Main())
    free_shapes = TDF_LabelSequence()
    shape_tool.GetFreeShapes(free_shapes)

    def _traverse_label(label: Any) -> XCAFComponent:
        entry_str = TDF_Tool.Entry(label)
        name_attr = TDataStd_Name()
        if label.FindAttribute(TDataStd_Name.GetID(), name_attr):
            name = name_attr.Get().ToExtString()
        else:
            name = entry_str

        is_assem = shape_tool.IsAssembly(label)
        shape = shape_tool.GetShape(label)
        children: list[XCAFComponent] = []

        if is_assem:
            sub_labels = TDF_LabelSequence()
            shape_tool.GetComponents(label, sub_labels)
            for i in range(1, sub_labels.Length() + 1):
                sub_label = sub_labels.Value(i)
                if shape_tool.IsComponent(sub_label):
                    ref_label = TDF_Label()
                    shape_tool.GetReferredShape(sub_label, ref_label)
                    children.append(_traverse_label(ref_label))
                else:
                    children.append(_traverse_label(sub_label))

        return XCAFComponent(
            label_entry=entry_str,
            name=name,
            is_assembly=is_assem,
            shape=shape,
            children=tuple(children),
        )

    roots: list[XCAFComponent] = []
    for i in range(1, free_shapes.Length() + 1):
        roots.append(_traverse_label(free_shapes.Value(i)))

    return roots
