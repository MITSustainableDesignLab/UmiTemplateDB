import hashlib
from datetime import datetime

import pycountry
from bson import DBRef as BaseDBRef
from mongoengine import *
from mongoengine import signals


class ReferenceField(ReferenceField):
    def to_mongo(self, document):
        if isinstance(document, DBRef):
            if not self.dbref:
                return document.id
            return document

        if isinstance(document, Document):
            # We need the id from the saved object to create the DBRef
            id_ = document.pk

            # XXX ValidationError raised outside of the "validate" method.
            if id_ is None:
                self.error(
                    "You can only reference documents once they have"
                    " been saved to the database"
                )

            # Use the attributes from the document instance, so that they
            # override the attributes of this field's document type
            cls = document
        else:
            id_ = document
            cls = self.document_type

        id_field_name = cls._meta["id_field"]
        id_field = cls._fields[id_field_name]

        id_ = id_field.to_mongo(id_)
        if self.document_type._meta.get("abstract"):
            collection = cls._get_collection_name()
            return DBRef(collection, id_, cls=cls._class_name)
        elif self.dbref:
            collection = cls._get_collection_name()
            return DBRef(collection, id_)

        return id_

    def to_python(self, value):
        """Convert a MongoDB-compatible type to a Python type."""
        if not self.dbref and not isinstance(
            value, (DBRef, Document, EmbeddedDocument)
        ):
            collection = self.document_type._get_collection_name()
            value = DBRef(collection, self.document_type.id.to_python(value))
        return value


class PrimaryKey(DictField):
    def __init__(self, field=None, *args, **kwargs):
        super().__init__(field=field, *args, **kwargs)

    # def to_mongo(self, value, use_db_field=True, fields=None):
    #     if isinstance(value, dict):
    #         return hash(value.values())
    #     else:
    #         return super(PrimaryKey, self).to_mongo(value, use_db_field=True, fields=None)


class DBRef(BaseDBRef):
    """Overrides the id property to have the {$ref: value} format"""

    @property
    def id(self):
        # create hasher
        hasher = hashlib.md5()
        hasher.update(self.__id.__str__().encode("utf-8"))  # Hashing the dict
        return {"$ref": hasher.hexdigest()}


class Document(Document):
    def to_dbref(self):
        """Returns an instance of :class:`~bson.dbref.DBRef` useful in
        `__raw__` queries."""
        if self.pk is None:
            msg = "Only saved documents can have a valid dbref"
            raise OperationError(msg)
        return DBRef(self.__class__._get_collection_name(), self.pk)

    meta = {"abstract": True}


class UmiBase(Document):
    """The Base class of all Umi objects.

    Attributes:
        Comments (StringField): Human readable string describing the exception.
        DataSource (StringField): Error code.
        Name (StringField): The Name of the Component. Required Field
        Category (StringField):

    """

    key = PrimaryKey(primary_key=True)
    Comments = StringField(null=True)
    DataSource = StringField(null=True)
    Name = StringField(required=True)
    Category = StringField(default="Uncategorized")

    meta = {"allow_inheritance": True}


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
    Type = StringField(default="Gas")
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
            "Smooth VerySmooth",
        ],
    )


def minimum_thickness(x):
    if x <= 0.003:
        print("Modeling layers thinner (less) than 0.003 m is not recommended")


class MaterialLayer(EmbeddedDocument):
    Material = ReferenceField(Material, required=True)
    Thickness = FloatField(validation=minimum_thickness, required=True)
    # key = EmbeddedDocumentField(PrimaryKey, primary_key=True)

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
    Category = StringField(
        choices=[
            "Facade",
            "Roof",
            "Ground Floor",
            "Interior Floor",
            "Exterior Floor",
            "Partition",
            "ThermalMass",
        ]
    )

    meta = {"allow_inheritance": True}


class WindowConstruction(ConstructionBase):
    Layers = EmbeddedDocumentListField(MaterialLayer)


class MassRatio(EmbeddedDocument):
    HighLoadRatio = FloatField(default=0.0)
    Material = ReferenceField(OpaqueMaterial, required=True)
    NormalRatio = FloatField(default=0.0)
    # key = EmbeddedDocumentField(PrimaryKey, primary_key=True)

    meta = {"allow_inheritance": True, "strict": False}


class StructureInformation(ConstructionBase):
    MassRatios = EmbeddedDocumentListField(MassRatio, required=True)


class DaySchedule(UmiBase):
    Type = StringField(default="Fraction")
    Values = ListField(
        FloatField(min_value=0, max_value=1), required=True, max_length=24
    )


class WeekSchedule(UmiBase):
    Days = ListField(ReferenceField(DaySchedule), required=True)
    Type = StringField(default="Fraction")


class YearSchedulePart(EmbeddedDocument):
    FromDay = IntField()
    FromMonth = IntField()
    ToDay = IntField()
    ToMonth = IntField()
    Schedule = ReferenceField(WeekSchedule, required=True)
    # key = EmbeddedDocumentField(PrimaryKey, primary_key=True)

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
    EconomizerType = IntField()
    HeatingCoeffOfPerf = FloatField()
    HeatingLimitType = IntField()
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
    Type = IntField(default=0)
    ZoneMixingAvailabilitySchedule = ReferenceField(YearSchedule, required=True)
    ZoneMixingDeltaTemperature = FloatField(default=2.0)
    ZoneMixingFlowRate = FloatField(default=0.001)


# A Bounding box for the whole world. Used as the default Polygon for BuildingTemplates.
world_poly = {
    "type": "Polygon",
    "coordinates": [[[-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]]],
}


def update_modified(sender, document):
    document.DateModified = datetime.utcnow()


class MetaData(EmbeddedDocument):
    """archetype template attributes

    Attributes:
        Author: (StringField):
        DateCreated (DateTimeField):
        DateModified (DateTimeField):
        Image (ImageField):
        Country (StringField):
        Description (StringField):

    """

    Author = StringField(required=True)
    DateCreated = DateTimeField(default=datetime.utcnow, required=True)
    DateModified = DateTimeField(default=datetime.utcnow)
    # Image = ImageField()

    Country = StringField(choices=[country.alpha_2 for country in pycountry.countries])
    YearFrom = StringField(
        help_text="Starting year for the range this template applies to"
    )
    YearTo = StringField(help_text="End year ")
    Polygon = PolygonField(default=world_poly)
    Description = StringField(help_text="")

    meta = {"allow_inheritance": True, "strict": False}

    signals.pre_save.connect(update_modified)


class BuildingTemplate(UmiBase):
    """Top most object in Umi Template Structure"""

    Core = ReferenceField(ZoneDefinition, required=True)
    Lifespan = IntField(default=60)
    PartitionRatio = FloatField(default=0)
    Perimeter = ReferenceField(ZoneDefinition, required=True)
    Structure = ReferenceField(StructureInformation, required=True)
    Windows = ReferenceField(WindowSetting, required=True)
    DefaultWindowToWallRatio = FloatField(default=0.4, min_value=0, max_value=1)
    MetaData = EmbeddedDocumentField(MetaData, required=True)
