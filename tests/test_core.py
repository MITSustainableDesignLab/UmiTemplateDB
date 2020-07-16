import datetime
import json
from tempfile import TemporaryFile

import pytest
from bson import ObjectId
from pymongo import MongoClient
from mockupdb import go, MockupDB
from pymongo.errors import DuplicateKeyError


class MockupDBDatabaseTest:
    def setUp(self):
        self.server = MockupDB(auto_ismaster={"maxWireVersion": 3})
        self.server.run()

        # Replace pymongo connection url to use MockupDB
        self.database = MongoDatabase(self.server.uri)

    def tearDown(self):
        self.server.stop()

    def list_documents(self, DOCUMENT):
        document = DOCUMENT

        # adding datetime object to document
        document["request_time"] = datetime.datetime.now()

        # The database list method converts any datetime object returned
        # from the database to string. See below.
        document_query = go(self.database.list, {})

        request = self.server.receives()

        # returns to pymongo a list containing only 1 the document
        request.reply([DOCUMENT])

        assert isinstance(document_query()[0]["request_time"], str)
        assert isinstance(
            document["request_time"].strftime("%Y-%m-%dT%H:%M:%S"),
            document_query()[0]["request_time"],
        )


class MongoDatabase(object):
    def __init__(self, uri):
        self.client = MongoClient(uri)
        self.db = self.client.db
        self.collection = self.db.collection

    def list(self, query):
        data_list = list()
        for data in self.collection.find(query):
            data["id"] = str(data.pop("_id"))
            data = self._convert_datetime_to_str(data)
            data_list.append(data)
        return data_list

    def _convert_datetime_to_str(self, data):
        for key in data.keys():
            if isinstance(data[key], datetime.datetime):
                data[key] = data[key].strftime("%Y-%m-%dT%H:%M:%S")
        return data


class TestImports:
    @pytest.fixture()
    def DOCUMENT(self):
        umi_template = "test_templates\BostonTemplateLibrary.json"
        with open(umi_template) as file:
            yield json.load(file)

    # @pytest.fixture(scope="module")
    # def db(self):
    #     db = MockupDBDatabaseTest()
    #     db.setUp()
    #     yield db
    #     db.tearDown()

    @pytest.fixture(scope="module")
    def db(self):
        client = MongoClient("mongodb://localhost:27017/")
        db = client["test"]
        yield db
        client.close()

    def test_import_umitemplate(self, db, DOCUMENT):

        assert db.list_documents(DOCUMENT)


    def test_import_library(self, db):
        import archetypal as ar
        from bson.json_util import loads

        def dict_generator(indict, pre=None):
            pre = pre[:] if pre else []
            if isinstance(indict, dict):
                for key, value in indict.items():
                    if isinstance(value, dict):
                        for d in dict_generator(value, pre + [key]):
                            yield d
                    elif isinstance(value, (list, tuple)):
                        for v in value:
                            for d in dict_generator(v, pre + [key]):
                                yield d
                    else:
                        yield pre + [key, value]
            else:
                yield pre + [indict]

        def recursive_ref(obj):
            if isinstance(obj, (dict)):
                for key, value in obj.items():
                    if isinstance(value, dict):
                        if "$ref" in value.keys():
                            ref = obj.get(key).get("$ref")
                            db_dict[f"{key}_id"] = ref
                    elif isinstance(value, list):
                        recursive_ref(value)
                    else:
                        db_dict[key] = value
            elif isinstance(obj, list):
                for value in obj:
                    recursive_ref(value)

        ut = ar.UmiTemplate.read_file(
            "test_templates\Ireland_UK_Tabula_Templates_Res.json"
        )
        with TemporaryFile() as buf:
            library_json = ut.to_dict()

        for coll, l in library_json.items():
            if isinstance(l, list):
                for document in l:
                    db_dict = {}
                    collection = db[coll]
                    try:
                        document["_id"] = document.pop("$id")
                        recursive_ref(document)
                        post_id = collection.insert(db_dict)
                        print(f"inserted {post_id}")
                    except DuplicateKeyError:
                        collection.replace_one({"_id": db_dict["_id"]}, db_dict, upsert=True)
                    except AttributeError as e:
                        raise e
                    except Exception as e:
                        raise e