from datetime import datetime

from pymongo import MongoClient
from mongoengine import *

import schema
import archetypal


def import_umitemplate(path):
    """Imports an UMI Template File to a mongodb client"""
    from archetypal import UmiTemplateLibrary

    # first, load the umitemplatelibrary
    lib = UmiTemplateLibrary.read_file(path)


    db_objs = {}  # dbobjects container

    # Loop over building templates
    for bldgtemplate in lib.__dict__["BuildingTemplates"]:

        def recursive(umibase):
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
            try:
                class_instance.save()
            except AttributeError:
                # Pass .save() on EmbeddedDocuments
                pass
            except ValidationError:
                pass
            db_objs[id(umibase)] = class_instance
            return class_instance

        # loop starts here
        recursive(bldgtemplate)
