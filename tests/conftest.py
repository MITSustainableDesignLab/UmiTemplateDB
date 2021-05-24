import pytest

from umitemplatedb.mongodb_schema import (
    BuildingTemplate,
    DaySchedule,
    WeekSchedule,
    YearSchedulePart,
    YearSchedule,
    ZoneConditioning,
    OpaqueMaterial,
    GlazingMaterial,
    MaterialLayer,
    OpaqueConstruction,
    GasMaterial,
    WindowConstruction,
    DomesticHotWaterSetting,
    ZoneConstructionSet,
    ZoneLoad,
    VentilationSetting,
    ZoneDefinition,
    MassRatio,
    StructureInformation,
    WindowSetting,
    GasLayer,
)


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
        Authors=["Samuel Letellier-Duchesne"],
        Country=["FRA"],
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
            "CoolingFuelType": 0,
            "HeatingFuelType": 0,
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
    return GasLayer(Material=air, Thickness=0.01)


@pytest.fixture()
def windowconstruction(windowlayer, airlayer):
    """
    Args:
        windowlayer:
        airlayer:
    """
    return WindowConstruction(
        Name="A Window Construction",
        Layers=[windowlayer, airlayer, windowlayer],
        Category="double",
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
def intmass(materiallayer):
    return OpaqueConstruction(Name="InternalMass", Layers=[materiallayer]).save()


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
