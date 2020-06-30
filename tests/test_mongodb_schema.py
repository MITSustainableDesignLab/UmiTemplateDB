from mongoengine import *
from schema.mongodb_schema import *
import pytest


@pytest.fixture
def db():
    connect("templatelibrary", host="mongomock://localhost")
    yield
    disconnect()


def test_add_building(bldg, window, struct, core):
    a_bldg = BuildingTemplate.objects().first()
    assert a_bldg.Name == bldg.Name


def test_to_json(bldg):
    print(bldg.to_json())


@pytest.fixture()
def bldg(db, core, struct, window):
    return BuildingTemplate(
        Name="Building One", Core=core, Perimeter=core, Structure=struct, Windows=window
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
    return WeekSchedule(Days=[days]).save()


@pytest.fixture()
def ys_part(weekschd):
    return YearSchedulePart(
        FromDay=0, FromMonth=0, ToDay=31, ToMonth=12, Schedule=weekschd
    )


@pytest.fixture()
def alwaysOn(ys_part):
    return YearSchedule(Name="AlwaysOn", Parts=[ys_part]).save()


@pytest.fixture()
def cond(alwaysOn):
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
    return MaterialLayer(Material=opaquematerial, Thickness=0.15)


@pytest.fixture()
def construction(materiallayer):
    return OpaqueConstruction(Name="A Construction", Layers=[materiallayer]).save()


@pytest.fixture()
def windowlayer(glazingmaterial):
    return MaterialLayer(Material=glazingmaterial, Thickness=0.01)


@pytest.fixture()
def air():
    return GasMaterial(Name="AIR").save()


@pytest.fixture()
def airlayer(air):
    return MaterialLayer(Material=air, Thickness=0.01)


@pytest.fixture()
def windowconstruction(windowlayer, airlayer):
    return WindowConstruction(
        Name="A Window Construction", Layers=[windowlayer, airlayer, windowlayer]
    ).save()


@pytest.fixture()
def dhw(alwaysOn):
    return DomesticHotWaterSetting(WaterSchedule=alwaysOn).save()


@pytest.fixture()
def conset(construction):
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
    return ZoneLoad(
        **{
            "EquipmentAvailabilitySchedule": alwaysOn,
            "LightsAvailabilitySchedule": alwaysOn,
            "OccupancySchedule": alwaysOn,
        }
    ).save()


@pytest.fixture()
def vent(alwaysOn):
    return VentilationSetting(
        **{"NatVentSchedule": alwaysOn, "ScheduledVentilationSchedule": alwaysOn}
    ).save()


@pytest.fixture()
def core(cond, conset, dhw, intmass, loads, vent):
    return ZoneDefinition(
        Name="Core Zone",
        **{
            "Conditioning": cond,
            "Constructions": conset,
            "DomesticHotWater": dhw,
            "InternalMassConstruction": intmass,
            "Loads": loads,
            "Ventilation": vent,
        }
    ).save()


@pytest.fixture()
def massratio(opaquematerial):
    return MassRatio(Material=opaquematerial)


@pytest.fixture()
def struct(massratio):
    return StructureInformation(MassRatio=[massratio]).save()


@pytest.fixture()
def window(alwaysOn, windowconstruction):
    return WindowSettings(
        **{
            "AfnWindowAvailability": alwaysOn,
            "Construction": windowconstruction,
            "ShadingSystemAvailabilitySchedule": alwaysOn,
            "ZoneMixingAvailabilitySchedule": alwaysOn,
        }
    ).save()


def test_building_template(db):

    assert BuildingTemplate.objects
