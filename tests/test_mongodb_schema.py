import json

import geojson
import pytest
import shapely.geometry
from archetypal import UmiTemplateLibrary

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
    a_bldg = BuildingTemplate.objects(Country="FR").first()
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
    pt = Point(42.370145, -71.112077)
    polygon = json.dumps(bldg.Polygon)
    # Convert to geojson.geometry.Polygon
    g1 = geojson.loads(polygon)
    g2 = shapely.geometry.shape(g1)
    # Check if intersection is True
    assert pt.intersects(g2)

    # Second, the actual filter with point pt
    ptj = shapely.geometry.mapping(pt)
    a_bldg = BuildingTemplate.objects(Polygon__geo_intersects=ptj).first()
    assert a_bldg


def test_import_library(db, imported):
    """Try using recursive"""
    for bldg in BuildingTemplate.objects():
        print(f"downloaded {bldg.Name}")
        assert bldg


def test_serialize_templatelist(bldg, window, struct, core):
    """From a list of :class:~`umitemplatedb.mongodb_schema.BuildingTemplate`
    create an :class:~`archetypal.umi_template.UmiTemplateLibrary`"""
    bldgs = [bldg]

    templates = []
    for bldg in bldgs:
        templates.append(bldg.to_template())

    lib = UmiTemplateLibrary(BuildingTemplates=templates)
    lib.to_json()


@pytest.fixture(scope="session")
def db():
    connect("templatelibrary", host="mongomock://localhost")
    # connect("templatelibrary")
    yield
    disconnect()


@pytest.fixture(scope="session")
def imported(db):
    path = "tests/test_templates/BostonTemplateLibrary.json"
    import_umitemplate(path, Author="Carlos Cerezo", Country="US")


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
        Author="Samuel Letellier-Duchesne",
        Country="FR",
    ).save()


@pytest.fixture()
def day():
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
        ],
        Name="DaySch",
    ).save()


@pytest.fixture()
def weekschd(day):
    """
    Args:
        days:
    """
    return WeekSchedule(Days=[day] * 7, Name="WeekSch").save()


@pytest.fixture()
def ys_part(weekschd):
    """
    Args:
        weekschd:
    """
    return YearSchedulePart(
        FromDay=1, FromMonth=1, ToDay=31, ToMonth=12, Schedule=weekschd
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
        },
        Name="Zone Conditioning",
    ).save()


@pytest.fixture()
def opaquematerial():
    return OpaqueMaterial(Name="OpaqueMaterial").save()


@pytest.fixture()
def glazingmaterial():
    return GlazingMaterial(Name="GlazingMaterial").save()


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
    return DomesticHotWaterSetting(
        WaterSchedule=alwaysOn, Name="DomesticHotWaterSetting"
    ).save()


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
        },
        Name="ZoneConstructionSet",
    ).save()


@pytest.fixture()
def intmass():
    return OpaqueConstruction(Name="OpaqueConstruction").save()


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
        },
        Name="ZoneLoad",
    ).save()


@pytest.fixture()
def vent(alwaysOn):
    """
    Args:
        alwaysOn:
    """
    return VentilationSetting(
        **{"NatVentSchedule": alwaysOn, "ScheduledVentilationSchedule": alwaysOn},
        Name="VentilationSetting",
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
    return StructureInformation(
        MassRatios=[massratio], Name="StructureInformation"
    ).save()


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
        },
        Name="WindowSetting",
    ).save()
