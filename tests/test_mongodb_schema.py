import json

import pytest
import shapely.geometry
from archetypal import UmiTemplateLibrary
from mongoengine import connect, disconnect, Q

from umitemplatedb.core import import_umitemplate
from umitemplatedb.mongodb_schema import *


def test_save_and_retrieve_building(bldg, window, struct, core):
    # To filter by an attribute of MetaData, use double underscore
    """
    Args:
        bldg:
        window:
        struct:
        core:
    """
    a_bldg = BuildingTemplate.objects(Country="FRA").first()
    assert a_bldg.Name == bldg.Name


@pytest.mark.xfail(
    condition=pytest.raises(NotImplementedError),
    reason="Not Implemented with Mongomock yet",
)
def test_filter_by_geo(bldg):
    """Shows how to filter database by geolocation.

    Hint:
        This is the logic: [building if <building.Polygon intersects pt> for
        building in BuildingTemplates]

        We would create the geoquery this way: First create a geojson-like dict
        using :meth:`shapely.geometry.mapping`. Then pass this pt to the
        `Polygon__geo_intersects` attribute. Polygon is the attribute of MetaData and finally,
        `geo_intersects` is the embedded MongoDB function for the `intersects`
        predicate. See `MongoEngine geo-queries`_ for more details.

    Args:
        bldg:

    .. _MongoEngine geo-queries:
        http://docs.mongoengine.org/guide/querying.html?highlight=geo_within#geo-queries
    """
    from shapely.geometry import Point

    # First, a sanity check. We build a pt and use
    # the :meth:`intersects` method.
    pt = Point(2, 46)  # Point inside France
    polygon = json.dumps(bldg.Polygon or bldg.MultiPolygon)
    # Convert to geojson.geometry.Polygon
    g1 = geojson.loads(polygon)
    g2 = shapely.geometry.shape(g1)
    # Check if intersection is True
    assert pt.within(g2)

    # Second, the actual filter with point pt
    ptj = shapely.geometry.mapping(pt)
    retreived_bldgs = BuildingTemplate.objects(
        Q(Polygon__geo_intersects=ptj) | Q(MultiPolygon__geo_intersects=ptj)
    ).all()
    assert all((bld.Country == "FRA" for bld in retreived_bldgs))


def test_import_library(db, imported):
    """Try using recursive"""
    for bldg in BuildingTemplate.objects():
        print(f"downloaded {bldg.Name}")
        assert bldg


def test_serialize_db(imported):
    bldgs = BuildingTemplate.objects().all()
    templates = []
    for bldg in bldgs:
        templates.append(bldg.to_template())
    lib = UmiTemplateLibrary(BuildingTemplates=templates).to_json()


def test_serialize_templatelist(bldg, window, struct, core):
    """From a list of :class:~`umitemplatedb.mongodb_schema.BuildingTemplate`
    create an :class:~`archetypal.umi_template.UmiTemplateLibrary`"""
    bldgs = [bldg]

    templates = []
    for bldg in bldgs:
        templates.append(bldg.to_template())

    lib = UmiTemplateLibrary(BuildingTemplates=templates)
    print(lib.to_json())


@pytest.fixture(scope="session")
def db():
    connect("templatelibrary", host="mongomock://localhost")
    # connect("templatelibrary")
    yield
    disconnect()


@pytest.fixture(scope="session")
def imported(db):
    UmiBase.drop_collection()

    path = "tests/test_templates/BostonTemplateLibrary.json"
    import_umitemplate(path)
