from App_FreeCAD.geometry_cache import clear_registry, get_or_create, get_part_graph_store
from MateCore.MateGraph.options import GraphBuildOptions


def test_get_or_create_separates_documents():
    clear_registry()
    assert get_or_create("A") is not get_or_create("B")
    assert get_or_create("A") is get_or_create("A")


def test_part_graph_store_is_singleton_per_document():
    clear_registry()
    a = get_part_graph_store("Doc1", GraphBuildOptions())
    b = get_part_graph_store("Doc1", GraphBuildOptions())
    assert a is b
