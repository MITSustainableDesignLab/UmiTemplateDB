import archetypal
import shapely.geometry
from mongoengine import *
import geopandas as gpd

import schema
from dbimport.core import import_umitemplate
from schema.mongodb_schema import *
import pytest
import json
import geojson


@pytest.fixture
def db():
    connect("templatelibrary", host="mongomock://localhost")
    # connect("templatelibrary")
    yield
    disconnect()


def test_retreive(db):
    assert BuildingTemplate.objects()


def test_save_and_retrieve_building(bldg, window, struct, core):
    # To filter by an attribute of MetaData, use double underscore
    """
    Args:
        bldg:
        window:
        struct:
        core:
    """
    a_bldg = BuildingTemplate.objects(MetaData__Country="FR").first()
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
        `MetaData__Polygon__geo_intersects` attribute. MetaData is the first
        Attribute. Polygon is the attribute of MetaData and finally,
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
    pt = Point(42.370145, -71.112077)
    polygon = json.dumps(bldg.MetaData.Polygon)
    # Convert to geojson.geometry.Polygon
    g1 = geojson.loads(polygon)
    g2 = shapely.geometry.shape(g1)
    # Check if intersection is True
    assert pt.intersects(g2)

    # Second, the actual filter with point pt
    ptj = shapely.geometry.mapping(pt)
    a_bldg = BuildingTemplate.objects(MetaData__Polygon__geo_intersects=ptj).first()
    assert a_bldg


def test_import_library(db):
    from archetypal import UmiTemplateLibrary

    lib = UmiTemplateLibrary.read_file(
        "tests/test_templates/BostonTemplateLibrary.json"
    )
    db_objs = {}
    for component_group in lib.__dict__.values():
        if isinstance(component_group, list):
            for component in component_group:
                class_ = getattr(schema.mongodb_schema, type(component).__name__)
                db_objs[component.id] = class_()

    assert db_objs
    assert lib


@pytest.fixture()
def imported(db):
    path = "tests/test_templates/BostonTemplateLibrary.json"
    import_umitemplate(path, Author="Carlos Cerezo", Country="US")


def test_import_library_(db, imported):
    """Try using recursive"""
    for bldg in BuildingTemplate.objects():
        print(f"downloaded {bldg}")
        assert bldg


def test_to_json(bldg):
    """
    Args:
        bldg:
    """
    print(bldg.to_json())


@pytest.fixture()
def bldg(db, core, struct, window):
    """
    Args:
        db:
        core:
        struct:
        window:
    """
    return BuildingTemplate(
        Name="Building One",
        Core=core,
        Perimeter=core,
        Structure=struct,
        Windows=window,
        MetaData=MetaData(Author="Samuel Letellier-Duchesne", Country="FR"),
    ).save()


@pytest.fixture()
def days():
    return DaySchedule(
        Values=[
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            0.7,
            0.3,
            0.3,
            0.3,
            0.3,
            0.3,
            0.3,
            0.3,
            0.3,
            0.3,
            0.7,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
        ]
    ).save()


@pytest.fixture()
def weekschd(days):
    """
    Args:
        days:
    """
    return WeekSchedule(Days=[days]).save()


@pytest.fixture()
def ys_part(weekschd):
    """
    Args:
        weekschd:
    """
    return YearSchedulePart(
        FromDay=0, FromMonth=0, ToDay=31, ToMonth=12, Schedule=weekschd
    )


@pytest.fixture()
def alwaysOn(ys_part):
    """
    Args:
        ys_part:
    """
    return YearSchedule(Name="AlwaysOn", Parts=[ys_part]).save()


@pytest.fixture()
def cond(alwaysOn):
    """
    Args:
        alwaysOn:
    """
    return ZoneConditioning(
        **{
            "CoolingSchedule": alwaysOn,
            "HeatingSchedule": alwaysOn,
            "MechVentSchedule": alwaysOn,
        }
    ).save()


@pytest.fixture()
def opaquematerial():
    return OpaqueMaterial().save()


@pytest.fixture()
def glazingmaterial():
    return GlazingMaterial().save()


@pytest.fixture()
def materiallayer(opaquematerial):
    """
    Args:
        opaquematerial:
    """
    return MaterialLayer(Material=opaquematerial, Thickness=0.15)


@pytest.fixture()
def construction(materiallayer):
    """
    Args:
        materiallayer:
    """
    return OpaqueConstruction(Name="A Construction", Layers=[materiallayer]).save()


@pytest.fixture()
def windowlayer(glazingmaterial):
    """
    Args:
        glazingmaterial:
    """
    return MaterialLayer(Material=glazingmaterial, Thickness=0.01)


@pytest.fixture()
def air():
    return GasMaterial(Name="AIR").save()


@pytest.fixture()
def airlayer(air):
    """
    Args:
        air:
    """
    return MaterialLayer(Material=air, Thickness=0.01)


@pytest.fixture()
def windowconstruction(windowlayer, airlayer):
    """
    Args:
        windowlayer:
        airlayer:
    """
    return WindowConstruction(
        Name="A Window Construction", Layers=[windowlayer, airlayer, windowlayer]
    ).save()


@pytest.fixture()
def dhw(alwaysOn):
    """
    Args:
        alwaysOn:
    """
    return DomesticHotWaterSetting(WaterSchedule=alwaysOn).save()


@pytest.fixture()
def conset(construction):
    """
    Args:
        construction:
    """
    return ZoneConstructionSet(
        **{
            "Facade": construction,
            "Ground": construction,
            "Partition": construction,
            "Roof": construction,
            "Slab": construction,
        }
    ).save()


@pytest.fixture()
def intmass():
    return OpaqueConstruction().save()


@pytest.fixture()
def loads(alwaysOn):
    """
    Args:
        alwaysOn:
    """
    return ZoneLoad(
        **{
            "EquipmentAvailabilitySchedule": alwaysOn,
            "LightsAvailabilitySchedule": alwaysOn,
            "OccupancySchedule": alwaysOn,
        }
    ).save()


@pytest.fixture()
def vent(alwaysOn):
    """
    Args:
        alwaysOn:
    """
    return VentilationSetting(
        **{"NatVentSchedule": alwaysOn, "ScheduledVentilationSchedule": alwaysOn}
    ).save()


@pytest.fixture()
def core(cond, conset, dhw, intmass, loads, vent):
    """
    Args:
        cond:
        conset:
        dhw:
        intmass:
        loads:
        vent:
    """
    return ZoneDefinition(
        Name="Core Zone",
        **{
            "Conditioning": cond,
            "Constructions": conset,
            "DomesticHotWater": dhw,
            "InternalMassConstruction": intmass,
            "Loads": loads,
            "Ventilation": vent,
        },
    ).save()


@pytest.fixture()
def massratio(opaquematerial):
    """
    Args:
        opaquematerial:
    """
    return MassRatio(Material=opaquematerial)


@pytest.fixture()
def struct(massratio):
    """
    Args:
        massratio:
    """
    return StructureInformation(MassRatio=[massratio]).save()


@pytest.fixture()
def window(alwaysOn, windowconstruction):
    """
    Args:
        alwaysOn:
        windowconstruction:
    """
    return WindowSetting(
        **{
            "AfnWindowAvailability": alwaysOn,
            "Construction": windowconstruction,
            "ShadingSystemAvailabilitySchedule": alwaysOn,
            "ZoneMixingAvailabilitySchedule": alwaysOn,
        }
    ).save()


def test_building_template(db):

    """
    Args:
        db:
    """
    assert BuildingTemplate.objects
