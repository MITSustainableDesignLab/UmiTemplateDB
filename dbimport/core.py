from datetime import datetime

from pymongo import MongoClient
from mongoengine import *

import schema
import archetypal

from schema.mongodb_schema import BuildingTemplate, PrimaryKey, MetaData


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
            if isinstance(
                class_,
                (
                    schema.mongodb_schema.YearSchedulePart,
                    schema.mongodb_schema.MaterialLayer,
                    schema.mongodb_schema.MetaData,
                    schema.mongodb_schema.MassRatio,
                ),
            ):
                pass
            else:
                instance_attr["key"] = PrimaryKey(
                    _name=instance_attr.get("Name", str(id(umibase))),
                    _class=type(class_).__name__,
                )
            class_instance = class_(**instance_attr)
            if isinstance(class_instance, BuildingTemplate):
                class_instance["MetaData"] = MetaData(**metaattributes)
            try:
                class_instance.save()
            except AttributeError:
                # Pass .save() on EmbeddedDocuments
                return class_instance
            except ValidationError as e:
                raise e
            else:
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
