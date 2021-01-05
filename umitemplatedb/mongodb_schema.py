import logging
from datetime import datetime

import geojson
import pycountry
from mongoengine import (
    BooleanField,
    DateTimeField,
    Document,
    EmbeddedDocument,
    EmbeddedDocumentListField,
    FloatField,
    IntField,
    ListField,
    MultiPolygonField,
    PolygonField,
    ReferenceField,
    StringField,
    ValidationError,
)
from pymongo import monitoring

import archetypal.template

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class CommandLogger(monitoring.CommandListener):
    def started(self, event):
        log.debug(
            "Command {0.command_name} with request id "
            "{0.request_id} started on server "
            "{0.connection_id}".format(event)
        )

    def succeeded(self, event):
        log.debug(
            "Command {0.command_name} with request id "
            "{0.request_id} on server {0.connection_id} "
            "succeeded in {0.duration_micros} "
            "microseconds".format(event)
        )

    def failed(self, event):
        log.debug(
            "Command {0.command_name} with request id "
            "{0.request_id} on server {0.connection_id} "
            "failed in {0.duration_micros} "
            "microseconds".format(event)
        )


monitoring.register(CommandLogger())


class CompoundKey(EmbeddedDocument):
    name = StringField(required=True)
    clsname = StringField(required=True)

    meta = {"allow_inheritance": True, "strict": False}


class UmiBase(Document):
    """The Base class of all Umi objects."""

    key = StringField(primary_key=True)

    Name = StringField(required=True, help_text="The name of the component")
    Comments = StringField(null=True, help_text="User-defined comments")
    DataSource = StringField(
        null=True, help_text="A reference to the source of the component"
    )
    Category = StringField(default="Uncategorized", help_text="")

    meta = {"allow_inheritance": True}

    def save(self, *args, **kwargs):
        """Little hack modifies the key to use a combination of class name and Name."""
        self.key = ", ".join([type(self).__name__, self.Name])
        return super(UmiBase, self).save(*args, **kwargs)


class Material(UmiBase):
    """MaterialBase."""

    Cost = FloatField(default=0.0, units=None)
    EmbodiedCarbon = FloatField(default=0.0, units="kgCO2/kg")
    EmbodiedEnergy = FloatField(default=0.0, units="MJ/kg")
    SubstitutionTimestep = FloatField(
        default=100,
        units="year",
        help_text="The duration in years of a period of replacement (e.g. There will "
        "be interventions in this material type every 10 years)",
    )
    SubstitutionRatePattern = ListField(
        default=[],
        units="dimensionless",
        help_text="a ratio from 0 to 1 which defines the amount of the material "
        "replaced at the end of each period of replacement (e.g. Every 10 "
        "years this cladding will be completely replaced with ratio 1)",
        long_help_text="Notice that you can define different replacement ratios for "
        "different consecutive periods, introducing them separated by "
        "commas. For example, if you introduce the series “[0.1 , 0.1 , "
        "1]” after the first 10 years (SubstitutionTimestep) 10% will "
        "be replaced, then after 20 years another 10%, then after 30 "
        "years 100%, and finally the series would start again in year "
        "40.",
    )
    TransportCarbon = FloatField(
        default=0.0,
        units="kgCO2/kg/km",
        help_text="Impacts associated with the transport by km of distance and kg of "
        "material",
    )
    TransportDistance = FloatField(
        default=0.0,
        units="km",
        help_text="The average distance in km from the manufacturing site to the "
        "building construction site",
        long_help_text="These values are typically defined by vehicle (Truck, Train, "
        "Boat, etc.) and size and can be found in fuel efficiency "
        "publications.",
    )
    TransportEnergy = FloatField(
        default=0.0,
        units="kgCO2/kg/km",
        help_text="Impacts associated with the transport by km of distance and kg of "
        "material",
        long_help_text="These values are typically defined by vehicle (Truck, Train, "
        "Boat, etc.) and size and can be found in fuel efficiency "
        "publications.",
    )
    Conductivity = FloatField(
        default=0,
        units="W/(m K)",
        help_text="The quantity of heat transmitted through a unit thickness of a "
        "material - in a direction normal to a surface of unit area - due to a unit "
        "temperature gradient under steady state conditions",
    )
    Density = FloatField(default=2500, units="kg/m³", help_text="Mass per unit volume.")


class GasMaterial(Material):
    GasType = IntField(0, choices=(0, 1, 2))
    Type = StringField(default="Gas")
    Life = FloatField(default=1)


class GlazingMaterial(Material):
    SolarTransmittance = FloatField(default=0, units=None)
    SolarReflectanceFront = FloatField(default=0, units=None)
    SolarReflectanceBack = FloatField(default=0, units=None)
    VisibleTransmittance = FloatField(default=0, units=None)
    VisibleReflectanceFront = FloatField(default=0, units=None)
    VisibleReflectanceBack = FloatField(default=0, units=None)
    IRTransmittance = FloatField(default=0, units=None)
    IREmissivityFront = FloatField(default=0, units=None)
    IREmissivityBack = FloatField(default=0, units=None)
    DirtFactor = FloatField(default=1.0, units=None)
    Type = StringField()
    Life = FloatField(default=1)


class OpaqueMaterial(Material):
    SpecificHeat = FloatField(default=0)
    SolarAbsorptance = FloatField(default=0.7)
    ThermalEmittance = FloatField(default=0.9)
    VisibleAbsorptance = FloatField(default=0.7)
    MoistureDiffusionResistance = FloatField(default=50)
    Roughness = StringField(
        default="Rough",
        choices=[
            "VeryRough",
            "Rough",
            "MediumRough",
            "MediumSmooth",
            "Smooth",
            "VerySmooth",
        ],
    )


class MaterialLayer(EmbeddedDocument):
    Material = ReferenceField(Material, required=True)
    Thickness = FloatField(required=True)

    meta = {"allow_inheritance": True, "strict": False}


class ConstructionBase(UmiBase):
    # Type = IntField(choices=range(0, 5))

    AssemblyCarbon = FloatField(default=0.0)
    AssemblyCost = FloatField(default=0.0)
    AssemblyEnergy = FloatField(default=0.0)
    DisassemblyCarbon = FloatField(default=0.0)
    DisassemblyEnergy = FloatField(default=0.0)


class OpaqueConstruction(ConstructionBase):
    Layers = EmbeddedDocumentListField(MaterialLayer)

    meta = {"allow_inheritance": True}


class WindowConstruction(ConstructionBase):
    Layers = EmbeddedDocumentListField(MaterialLayer)


class MassRatio(EmbeddedDocument):
    HighLoadRatio = FloatField(default=0.0)
    Material = ReferenceField(OpaqueMaterial, required=True)
    NormalRatio = FloatField(default=0.0)

    meta = {"allow_inheritance": True, "strict": False}


class StructureInformation(ConstructionBase):
    MassRatios = EmbeddedDocumentListField(MassRatio, required=True)


class DaySchedule(UmiBase):
    Type = StringField(default="Fraction")
    Values = ListField(
        FloatField(min_value=0, max_value=1), required=True, max_length=24
    )


def min_length(x):
    """WeekSchedule.Days should have length == 7"""
    if len(x) != 7:
        raise ValidationError


class WeekSchedule(UmiBase):
    Days = ListField(ReferenceField(DaySchedule), validation=min_length, required=True)
    Type = StringField(default="Fraction")


class YearSchedulePart(EmbeddedDocument):
    FromDay = IntField(min_value=1, max_value=31)
    FromMonth = IntField(min_value=1, max_value=12)
    ToDay = IntField(min_value=1, max_value=31)
    ToMonth = IntField(min_value=1, max_value=12)
    Schedule = ReferenceField(WeekSchedule, required=True)

    meta = {"allow_inheritance": True, "strict": False}


class YearSchedule(UmiBase):
    Parts = EmbeddedDocumentListField(YearSchedulePart, required=True)
    Type = StringField(default="Fraction")


class DomesticHotWaterSetting(UmiBase):
    FlowRatePerFloorArea = FloatField(default=0.03)
    IsOn = BooleanField(default=True)
    WaterSchedule = ReferenceField(YearSchedule, required=True)
    WaterSupplyTemperature = FloatField(default=65)
    WaterTemperatureInlet = FloatField(default=10)


class VentilationSetting(UmiBase):
    Afn = BooleanField(default=False)
    IsBuoyancyOn = BooleanField(default=True)
    Infiltration = FloatField(default=0.1)
    IsInfiltrationOn = BooleanField(default=True)
    IsNatVentOn = BooleanField(default=False)
    IsScheduledVentilationOn = BooleanField(default=False)
    NatVentMaxRelHumidity = FloatField(default=90, min_value=0, max_value=100)
    NatVentMaxOutdoorAirTemp = FloatField(default=30)
    NatVentMinOutdoorAirTemp = FloatField(default=0)
    NatVentSchedule = ReferenceField(YearSchedule, required=True)
    NatVentZoneTempSetpoint = FloatField(default=18)
    ScheduledVentilationAch = FloatField(default=0.6)
    ScheduledVentilationSchedule = ReferenceField(YearSchedule, required=True)
    ScheduledVentilationSetpoint = FloatField(default=18)
    IsWindOn = BooleanField(default=False)


class ZoneConditioning(UmiBase):
    CoolingSchedule = ReferenceField(YearSchedule, required=True)
    CoolingCoeffOfPerf = FloatField()
    CoolingSetpoint = FloatField(default=26)
    CoolingLimitType = IntField()
    CoolingFuelType = IntField(required=True)
    EconomizerType = IntField()
    HeatingCoeffOfPerf = FloatField()
    HeatingLimitType = IntField()
    HeatingFuelType = IntField(required=True)
    HeatingSchedule = ReferenceField(YearSchedule, required=True)
    HeatingSetpoint = FloatField(default=20)
    HeatRecoveryEfficiencyLatent = FloatField(min_value=0, max_value=1, default=0.65)
    HeatRecoveryEfficiencySensible = FloatField(min_value=0, max_value=1, default=0.7)
    HeatRecoveryType = IntField()
    IsCoolingOn = BooleanField(default=True)
    IsHeatingOn = BooleanField(default=True)
    IsMechVentOn = BooleanField(default=True)
    MaxCoolFlow = FloatField(default=100)
    MaxCoolingCapacity = FloatField(default=100)
    MaxHeatFlow = FloatField(default=100)
    MaxHeatingCapacity = FloatField(default=100)
    MechVentSchedule = ReferenceField(YearSchedule, required=True)
    MinFreshAirPerArea = FloatField(default=0.001)
    MinFreshAirPerPerson = FloatField(default=0.001)


class ZoneConstructionSet(UmiBase):
    Facade = ReferenceField(OpaqueConstruction, required=True)
    Ground = ReferenceField(OpaqueConstruction, required=True)
    Partition = ReferenceField(OpaqueConstruction, required=True)
    Roof = ReferenceField(OpaqueConstruction, required=True)
    Slab = ReferenceField(OpaqueConstruction, required=True)
    IsFacadeAdiabatic = BooleanField(default=False)
    IsGroundAdiabatic = BooleanField(default=False)
    IsPartitionAdiabatic = BooleanField(default=False)
    IsRoofAdiabatic = BooleanField(default=False)
    IsSlabAdiabatic = BooleanField(default=False)


class ZoneLoad(UmiBase):
    DimmingType = IntField()
    EquipmentAvailabilitySchedule = ReferenceField(YearSchedule, required=True)
    EquipmentPowerDensity = FloatField(default=12)
    IlluminanceTarget = FloatField(default=500)
    LightingPowerDensity = FloatField(default=12)
    LightsAvailabilitySchedule = ReferenceField(YearSchedule, required=True)
    OccupancySchedule = ReferenceField(YearSchedule, required=True)
    IsEquipmentOn = BooleanField(default=True)
    IsLightingOn = BooleanField(default=True)
    IsPeopleOn = BooleanField(default=True)
    PeopleDensity = FloatField(default=0.2)


class ZoneDefinition(UmiBase):
    Conditioning = ReferenceField(ZoneConditioning, required=True)
    Constructions = ReferenceField(ZoneConstructionSet, required=True)
    DaylightMeshResolution = FloatField(default=1)
    DaylightWorkplaneHeight = FloatField(default=0.8)
    DomesticHotWater = ReferenceField(DomesticHotWaterSetting, required=True)
    InternalMassConstruction = ReferenceField(OpaqueConstruction, required=True)
    InternalMassExposedPerFloorArea = FloatField()
    Loads = ReferenceField(ZoneLoad, required=True)
    Ventilation = ReferenceField(VentilationSetting, required=True)


class WindowSetting(UmiBase):
    AfnDischargeC = FloatField(default=0.65, min_value=0, max_value=1)
    AfnTempSetpoint = FloatField(default=20)
    AfnWindowAvailability = ReferenceField(YearSchedule, required=True)
    Construction = ReferenceField(WindowConstruction, required=True)
    IsShadingSystemOn = BooleanField(default=True)
    IsVirtualPartition = BooleanField()
    IsZoneMixingOn = BooleanField()
    OperableArea = FloatField(default=0.8, min_value=0, max_value=1)
    ShadingSystemAvailabilitySchedule = ReferenceField(YearSchedule, required=True)
    ShadingSystemSetpoint = FloatField(default=180)
    ShadingSystemTransmittance = FloatField(default=0.5)
    ShadingSystemType = IntField()
    Type = IntField()
    ZoneMixingAvailabilitySchedule = ReferenceField(YearSchedule, required=True)
    ZoneMixingDeltaTemperature = FloatField(default=2.0)
    ZoneMixingFlowRate = FloatField(default=0.001)


# A Bounding box for the whole world. Used as the default Polygon
# for BuildingTemplates.
world_poly = {
    "type": "Polygon",
    "coordinates": [[[-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]]],
}


class ClimateZone(Document):
    """A class to store climate zone geometries"""

    CZ = StringField()
    ISO3_CODE = StringField()
    geometry = PolygonField()


class BuildingTemplate(UmiBase):
    """Top most object in Umi Template Structure"""

    _geo_countries = None
    _available_countries = tuple((a.alpha_3, a.name) for a in list(pycountry.countries))

    Core = ReferenceField(ZoneDefinition, required=True)
    Lifespan = IntField(default=60)
    PartitionRatio = FloatField(default=0)
    Perimeter = ReferenceField(ZoneDefinition, required=True)
    Structure = ReferenceField(StructureInformation, required=True)
    Windows = ReferenceField(WindowSetting, required=True)
    DefaultWindowToWallRatio = FloatField(default=0.4, min_value=0, max_value=1)

    # MetaData
    Authors = ListField(StringField())
    AuthorEmails = ListField(StringField())
    DateCreated = DateTimeField(default=datetime.utcnow, required=True)
    DateModified = DateTimeField(default=datetime.utcnow)
    Country = ListField(StringField(choices=_available_countries))
    YearFrom = IntField(help_text="Template starting year")
    YearTo = IntField(help_text="End year")
    ClimateZone = ListField(StringField())
    Polygon = PolygonField()
    MultiPolygon = MultiPolygonField()
    Description = StringField()
    Version = StringField()

    def to_template(self, idf=None):
        """Converts to an :class:~`archetypal.template.building_template
        .BuildingTemplate` object"""

        def recursive(document, idf):
            """recursively create UmiBase objects from Document objects. Start with
            BuildingTemplates."""
            instance_attr = {}
            class_ = getattr(archetypal.template, type(document).__name__)
            for key in document:
                if isinstance(document[key], (UmiBase, YearSchedulePart)):
                    instance_attr[key] = recursive(document[key], idf)
                elif isinstance(document[key], list):
                    instance_attr[key] = []
                    for value in document[key]:
                        if isinstance(
                            value,
                            (UmiBase, YearSchedulePart, MaterialLayer, MassRatio,),
                        ):
                            instance_attr[key].append(recursive(value, idf))
                        else:
                            instance_attr[key].append(value)
                elif isinstance(document[key], (str, int, float)):
                    instance_attr[key] = document[key]
            class_instance = class_(**instance_attr, idf=idf)
            return class_instance

        if idf is None:
            from archetypal import IDF

            idf = IDF()

        return recursive(self, idf=idf)

    def save(self, *args, **kwargs):
        if not self.Polygon and self.Country:
            geometry = next(
                filter(
                    lambda x: x["properties"]["ISO_A3"] in self.Country,
                    self.geo_countries,
                ),
                None,
            )
            if geometry is not None:
                geometry = geometry.geometry  # get actual geom
                if isinstance(geometry, geojson.MultiPolygon):
                    self.MultiPolygon = geometry  # set to MultiPolygon
                elif isinstance(geometry, geojson.Polygon):
                    self.Polygon = geometry  # set to Polygon
                else:
                    raise TypeError(
                        f"cannot import geometry of type '{type(geometry)}'. "
                        f"Only 'Polygon' and 'MultiPolygon' are supported"
                    )
        return super(BuildingTemplate, self).save(*args, **kwargs)

    @property
    def geo_countries(self):
        if self._geo_countries is None:
            from datapackage import Package

            try:
                package = Package(
                    "https://datahub.io/core/geo-countries/datapackage" ".json"
                )
            except Exception:
                self._geo_countries = []
            else:
                f = package.get_resource("countries").raw_read()
                self._geo_countries = geojson.loads(f).features
        return self._geo_countries
