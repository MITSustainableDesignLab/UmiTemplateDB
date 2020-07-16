from datetime import datetime

from pymongo import MongoClient
from mongoengine import *


def import_umitemplate(path, client, db):
    """Imports an UMI Template File to a mongodb client"""
    pass


class MetaData:
    def __init__(
        self, date_created, date_modified, author, description, archetype_type
    ):
        """

        Args:
            date_created:
            date_modified:
            author:
            description:
            archetype_type (str): "reference" or "prototype". New constructions
                should be based on "prototype" buildings (according to code).
        """
        self.date_created = datetime(date_created)
        self.date_modified = date_modified
        self.author = author
        self.description = description

        self.archetype_type = archetype_type
