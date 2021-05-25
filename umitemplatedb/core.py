import logging
from enum import Enum

from archetypal.umi_template import traverse
from mongoengine import EmbeddedDocument
from tqdm import tqdm

import archetypal
from umitemplatedb import mongodb_schema
from umitemplatedb.mongodb_schema import BuildingTemplate

log = logging.getLogger(__name__)


def import_umitemplate(filename, **kwargs):
    """Imports an UMI Template File to a mongodb client

    Args:
        filename (str or Path): PathLike object giving the pathname (absolute
                or relative to the current working directory) of the UMI
                Template File.
        **kwargs: keyword arguments added to the BuildingTemplate class.
    """
    from archetypal import UmiTemplateLibrary

    # first, load the umitemplatelibrary
    lib = UmiTemplateLibrary.open(filename)

    # Loop over building templates
    for bldgtemplate in tqdm(lib.BuildingTemplates, desc="importing templates"):

        def recursive(umibase, **metaattributes):
            """recursively create db objects from UmiBase objects. Start with
            BuildingTemplates."""
            instance_attr = {}
            class_ = getattr(mongodb_schema, type(umibase).__name__)
            for key, value in umibase.mapping().items():
                if isinstance(
                    value,
                    (
                        archetypal.template.umi_base.UmiBase,
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
                                archetypal.template.umi_base.UmiBase,
                                archetypal.template.schedule.YearSchedulePart,
                                archetypal.template.materials.material_layer.MaterialLayer,
                                archetypal.template.materials.gas_layer.GasLayer,
                                archetypal.template.structure.MassRatio,
                            ),
                        ):
                            instance_attr[key].append(recursive(value))
                        else:
                            instance_attr[key].append(value)
                elif isinstance(value, (str, int, float)):
                    instance_attr[key] = value
                elif isinstance(value, Enum):
                    instance_attr[key] = value.value
            class_instance = class_(**instance_attr)
            if isinstance(class_instance, EmbeddedDocument):
                return class_instance
            else:
                class_instance = class_(
                    **instance_attr,
                )
                if isinstance(class_instance, BuildingTemplate):
                    for key, value in metaattributes.items():
                        class_instance[key] = value
                class_instance.save()
                return class_instance

        # loop starts here
        recursive(bldgtemplate, **kwargs)
