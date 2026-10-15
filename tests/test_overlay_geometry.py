from types import SimpleNamespace

from App_FreeCAD.rendering.overlay_geometry import (
    tessellate_surface_global,
    transform_vertices,
)


def test_transform_vertices_applies_global_placement():
    placement = SimpleNamespace(
        multVec=lambda v: SimpleNamespace(x=v.x + 5, y=v.y + 1, z=v.z - 2)
    )
    verts = [SimpleNamespace(x=1.0, y=2.0, z=3.0)]
    assert transform_vertices(verts, placement) == [(6.0, 3.0, 1.0)]


def test_tessellate_surface_global_uses_owner_placement():
    v = SimpleNamespace(x=0.0, y=0.0, z=0.0)
    face = SimpleNamespace(
        tessellate=lambda tol: ([v], [(0, 0, 0)]),
    )
    owner = SimpleNamespace(
        getGlobalPlacement=lambda: SimpleNamespace(
            multVec=lambda p: SimpleNamespace(x=10.0, y=0.0, z=0.0)
        ),
        Shape=SimpleNamespace(getElement=lambda name: face),
    )
    surface = SimpleNamespace(
        face_name="Face1",
        shape=face,
        owner=owner,
    )
    vertices, facets = tessellate_surface_global(surface, 0.1)
    assert vertices == [(10.0, 0.0, 0.0)]
    assert facets == [(0, 0, 0)]
