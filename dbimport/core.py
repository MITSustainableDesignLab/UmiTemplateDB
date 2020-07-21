import hashlib
import json

import archetypal
import numpy as np
from mongoengine import *

import schema
from schema.mongodb_schema import (
    BuildingTemplate,
    MetaData,
    GasMaterial,
    GlazingMaterial,
    OpaqueMaterial,
    OpaqueConstruction,
    WindowConstruction,
    StructureInformation,
    DaySchedule,
    WeekSchedule,
    YearSchedule,
    DomesticHotWaterSetting,
    VentilationSetting,
    ZoneConditioning,
    ZoneConstructionSet,
    ZoneLoad,
    ZoneDefinition,
    WindowSetting,
)


def import_umitemplate(
    filename,
    Author=None,
    Country=None,
    YearFrom=None,
    YearTo=None,
    Polygon=None,
    Description=None,
):
    """Imports an UMI Template File to a mongodb client

    Args:
        filename (str or Path): PathLike object giving the pathname (absolute
                or relative to the current working directory) of the UMI
                Template File.
        Author (str): The author of the template library. Saved in the dababase
            metadata.
        Country (str): The 2-letter country code. See pycountry.
        YearFrom (str): Starting year for the range this template applies to. All
            building templates are assumed to have the same YearFrom value.
        YearTo (str): End year for the range this template applies to. All
            building templates are assumed to have the same YearFrom value.
        Polygon (shapely.polygon):
        Description (str):
    """
    from archetypal import UmiTemplateLibrary

    # first, load the umitemplatelibrary
    lib = UmiTemplateLibrary.read_file(filename)

    # Loop over building templates
    for bldgtemplate in lib.__dict__["BuildingTemplates"]:

        def recursive(umibase, **metaattributes):
            """recursively create db objects from UmiBase objects. Start with
            BuildingTemplates."""
            instance_attr = {}
            class_ = getattr(schema.mongodb_schema, type(umibase).__name__)
            for key, value in umibase.mapping().items():
                if isinstance(
                    value,
                    (
                        archetypal.template.UmiBase,
                        archetypal.template.schedule.YearSchedulePart,
                    ),
                ):
                    instance_attr[key] = recursive(value)
                elif isinstance(value, list):
                    instance_attr[key] = []
                    for value in value:
                        if isinstance(
                            value,
                            (
                                archetypal.template.UmiBase,
                                archetypal.template.schedule.YearSchedulePart,
                                archetypal.template.MaterialLayer,
                                archetypal.template.MassRatio,
                            ),
                        ):
                            instance_attr[key].append(recursive(value))
                        else:
                            instance_attr[key].append(value)
                elif isinstance(value, (str, int, float)):
                    instance_attr[key] = value
            class_instance = class_(**instance_attr)
            if isinstance(class_instance, EmbeddedDocument):
                return class_instance
            else:
                class_instance = class_(
                    **instance_attr,
                    key=dict(
                        _name=instance_attr.get("Name", id(umibase).__str__()),
                        _class=type(umibase).__name__,
                    )
                )
                if isinstance(class_instance, BuildingTemplate):
                    class_instance["MetaData"] = MetaData(**metaattributes)
                class_instance.save()
                return class_instance

        # loop starts here
        bldg = recursive(
            bldgtemplate,
            Author=Author,
            Country=Country,
            YearFrom=YearFrom,
            YearTo=YearTo,
            Polygon=Polygon,
            Description=Description,
        )


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, QuerySet):
            return [obj.to_json(cls=CustomJSONEncoder) for obj in obj]
        return json.JSONEncoder.default(self, obj)


class MongoEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Document):
            data = o.to_mongo()
            _class = data.pop("_cls")
            return data
        return o.to_json()


def serialize():
    data = {
        "GasMaterials": [obj.to_json(indent=3) for obj in GasMaterial.objects()],
        "GlazingMaterials": [
            obj.to_json(indent=3) for obj in GlazingMaterial.objects()
        ],
        "OpaqueMaterials": [obj.to_json(indent=3) for obj in OpaqueMaterial.objects()],
        "OpaqueConstructions": [
            obj.to_json(indent=3) for obj in OpaqueConstruction.objects()
        ],
        "WindowConstructions": [
            obj.to_json(indent=3) for obj in WindowConstruction.objects()
        ],
        "StructureDefinitions": [
            obj.to_json(indent=3) for obj in StructureInformation.objects()
        ],
        "DaySchedules": [obj.to_json(indent=3) for obj in DaySchedule.objects()],
        "WeekSchedules": [obj.to_json(indent=3) for obj in WeekSchedule.objects()],
        "YearSchedules": [obj.to_json(indent=3) for obj in YearSchedule.objects()],
        "DomesticHotWaterSettings": [
            obj.to_json(indent=3) for obj in DomesticHotWaterSetting.objects()
        ],
        "VentilationSettings": [
            obj.to_json(indent=3) for obj in VentilationSetting.objects()
        ],
        "ZoneConditionings": [
            obj.to_json(indent=3) for obj in ZoneConditioning.objects()
        ],
        "ZoneConstructionSets": [
            obj.to_json(indent=3) for obj in ZoneConstructionSet.objects()
        ],
        "ZoneLoads": [obj.to_json(indent=3) for obj in ZoneLoad.objects()],
        "Zones": [obj.to_json(indent=3) for obj in ZoneDefinition.objects()],
        "WindowSettings": [obj.to_json(indent=3) for obj in WindowSetting.objects()],
        "BuildingTemplates": [
            obj.to_json(indent=3)
            for obj in BuildingTemplate.objects().exclude("MetaData", "_cls")
        ],
    }

    class CustomJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, np.bool_):
                return bool(obj)
            return obj

    with open("data.json", "w") as outfile:
        # create hasher
        data_dict = {}
        for name, block in data.items():
            data_dict[name] = [json.loads(item) for item in block]
            for component in data_dict[name]:
                _id = component.pop("_id")  # Gets rid of the _id field
                _cls = component.pop("_cls")  # Gets rid of the _cls field
                _name = component["Name"]  # Gets the component Name

                hasher = hashlib.md5()
                hasher.update(_id.__str__().encode("utf-8"))
                component["$id"] = hasher.hexdigest()  # re-creates the unique id
                for key, value in component.items():
                    if isinstance(value, list):
                        try:
                            [value.pop("_cls", None) for value in value]
                        except AttributeError:
                            pass
        response = json.dumps(data_dict, indent=3, cls=CustomJSONEncoder)
        outfile.write(response)
