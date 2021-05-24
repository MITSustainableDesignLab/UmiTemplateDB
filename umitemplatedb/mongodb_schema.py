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


# Uncomment next line to register the logger
# monitoring.register(CommandLogger())


class CompoundKey(EmbeddedDocument):
    name = StringField(required=True)
    clsname = StringField(required=True)

    meta = {"allow_inheritance": True, "strict": False}


class UmiBase(Document):
    """The Base class of all Umi objects.

    Attributes:
        Comments (StringField): Human readable string describing the exception.
        DataSource (StringField): Error code.
        Name (StringField): The Name of the Component. Required Field
        Category (StringField):

    """

    key = StringField(primary_key=True)

    Name = StringField(required=True)
    Comments = StringField(null=True)
    DataSource = StringField(null=True)
    Category = StringField(default="Uncategorized")

    meta = {"allow_inheritance": True}

    def save(self, *args, **kwargs):
        self.key = ", ".join([type(self).__name__, self.Name])
        return super(UmiBase, self).save(*args, **kwargs)


class Material(UmiBase):
    # MaterialBase
    Cost = FloatField(default=0.0)
    EmbodiedCarbon = FloatField(default=0.0)
    EmbodiedEnergy = FloatField(default=0.0)
    SubstitutionTimestep = FloatField(default=100)
    TransportCarbon = FloatField(default=0.0)
    TransportDistance = FloatField(default=0.0)
    TransportEnergy = FloatField(default=0.0)
    SubstitutionRatePattern = ListField(default=[])
    Conductivity = FloatField(default=0)
    Density = FloatField(default=2500)


class GasMaterial(Material):
    GasType = IntField(0, choices=(0, 1, 2))
    Type = StringField(default="Air")
    Life = FloatField(default=1)


class GlazingMaterial(Material):
    SolarTransmittance = FloatField(default=0)
    SolarReflectanceFront = FloatField(default=0)
    SolarReflectanceBack = FloatField(default=0)
    VisibleTransmittance = FloatField(default=0)
    VisibleReflectanceFront = FloatField(default=0)
    VisibleReflectanceBack = FloatField(default=0)
    IRTransmittance = FloatField(default=0)
    IREmissivityFront = FloatField(default=0)
    IREmissivityBack = FloatField(default=0)
    DirtFactor = FloatField(default=1.0)
    Type = StringField()
    Life = FloatField(default=1)


class OpaqueMaterial(Material):
    SpecificHeat = FloatField(default=100, min_value=100)
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


class _Layer(EmbeddedDocument):
    """Parent class of MaterialLayer & GasLayer to use in EmbeddedDocumentListField."""

    pass

    meta = {"allow_inheritance": True}


class MaterialLayer(_Layer):
    Material = ReferenceField(Material, required=True)
    Thickness = FloatField(required=True)

    meta = {"allow_inheritance": True, "strict": False}


class GasLayer(_Layer):
    Material = ReferenceField(GasMaterial, required=True)
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
    Layers = EmbeddedDocumentListField(_Layer)

    meta = {"allow_inheritance": True}


class WindowConstruction(ConstructionBase):
    Layers = EmbeddedDocumentListField(_Layer)


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
    """WeekSchedule.Days should have lenght == 7"""
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

    zone_surfaces = ListField()
    is_part_of_conditioned_floor_area = BooleanField(default=True)
    volume = FloatField()
    multiplier = IntField(min_value=1)
    occupants = FloatField()
    is_part_of_total_floor_area = BooleanField(default=True)
    area = FloatField()
    is_core = BooleanField()


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

    def to_template(self, idf=None, bar=None):
        """Converts to an :class:~`archetypal.template.building_template
        .BuildingTemplate` object.

        Args:
            idf (IDF): Optional, an IDF object.
            bar (tqdm): A tqdm progress bar, optional.

        Returns:
            (archetypal.template.BuildingTemplate): The BuildingTemplate object.
        """

        def recursive(document, idf, bar):
            """recursively create UmiBase objects from Document objects. Start with
            BuildingTemplates."""
            if bar is not None:
                bar.update(1)
            instance_attr = {}
            class_ = getattr(archetypal.template, type(document).__name__)
            for key in document:
                if isinstance(document[key], (UmiBase, YearSchedulePart)):
                    instance_attr[key] = recursive(document[key], idf, bar)
                elif isinstance(document[key], list):
                    instance_attr[key] = []
                    for value in document[key]:
                        if isinstance(
                            value,
                            (
                                UmiBase,
                                YearSchedulePart,
                                MaterialLayer,
                                GasLayer,
                                MassRatio,
                            ),
                        ):
                            instance_attr[key].append(recursive(value, idf, bar))
                        else:
                            instance_attr[key].append(value)
                elif isinstance(document[key], (str, int, float)):
                    instance_attr[key] = document[key]
            class_instance = class_(**instance_attr, idf=idf)
            return class_instance

        if idf is None:
            from archetypal import IDF

            idf = IDF()
        return recursive(self, idf=idf, bar=bar)

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
        if BuildingTemplate._geo_countries is None:
            from datapackage import Package

            try:
                package = Package(
                    "https://datahub.io/core/geo-countries/datapackage.json"
                )
            except Exception as e:
                log.error(
                    "An error occurred while loading country polygons from datahub.io",
                    exc_info=e,
                )
                BuildingTemplate._geo_countries = []
            else:
                f = package.get_resource("countries").raw_read()
                BuildingTemplate._geo_countries = geojson.loads(f).features
                log.info("Country Polygons loaded from datahub.io")
        return self._geo_countries
