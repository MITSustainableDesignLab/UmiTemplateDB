import archetypal
from mongoengine import *

from umitemplatedb import mongodb_schema
from umitemplatedb.mongodb_schema import (
    BuildingTemplate,
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
            class_ = getattr(mongodb_schema, type(umibase).__name__)
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
                    for key, value in metaattributes.items():
                        class_instance[key] = value
                class_instance.save()
                return class_instance

        if not Polygon:
            Polygon = {
                "type": "Polygon",
                "coordinates": [
                    [[-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]]
                ],
            }

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