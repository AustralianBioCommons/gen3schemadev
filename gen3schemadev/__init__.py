import glob
import os
import yaml
from enum import Enum
from .gen3properties import Gen3Property, Gen3DatetimeProperty, Gen3JsonProperty, Gen3Enum, Gen3Integer, Gen3Number, \
    Gen3Boolean, Gen3String, Gen3WrapObject
from typing import List
from abc import abstractmethod


class Gen3Context:
    """the context of a variable within a bundle, essentially equivalent to a string of the format
    filenae#xpathselector (Xpath is a query language)
    Only chold selector used"""

    def __init__(self, filename, path):
        self.filename = filename
        if isinstance(path, str):
            self.path = [path]
        elif isinstance(path, list):
            self.path = path
        else:
            raise NotImplemented()

    @staticmethod
    def parse_id(idstr: str):
        """parse a refstring and return a filename,path pair"""
        a = idstr.split("#")
        a[1] = a[1][1:].split("/")
        return a

    def __eq__(self, other):
        """Overrides the default implementation"""
        if isinstance(other, Gen3Context):
            return self.__repr__() == other.__repr__()
        return False

    def get_subcontext(self, path):
        """
        returns the context that is path deeper than self
        :param path: the path
        :return: Context
        """
        rv = Gen3Context(self.filename, self.path.copy())
        rv.path.append(path)
        return rv

    def __repr__(self):
        tmp_str = self.filename
        return tmp_str + "#" + "/".join(self.path)


class Gen3Term:
    """A term defined in a file within a context. A term is either list or string"""

    def __init__(self, value, context):
        self.value = value
        self.context = context

    def __repr__(self):
        return self.context.__repr__() + ": " + self.value


class Gen3Object(Gen3WrapObject):
    class CATEGORY(Enum):
        ADMINISTRATIVE = "administrative"
        ANALYSIS = "analysis"
        BIOSPECIMEN = "biospecimen"
        CLINICAL = "clinical"
        DATA_FILE = "data_file"
        EXPERIMENTAL_METHODS = "experimental_methods"
        INDEX_FILE = "index_file"
        METADATA_FILE = "metadata_file"
        NOTATION = "notation"
        STUDY_ADMINISTRATION = "study_administration"

    """
    A wrapper object around a gen3 object data is stored in the data dictionary.
    """

    def __init__(self, filename, data):
        self.filename = filename
        self.data = data.copy()
        if "$schema" not in self.data:
            self.data["$schema"] = "http://json-schema.org/draft-04/schema#"

    def __getattribute__(self, item):
        """
        Python magic in progress. this will redirect all property accesses to the
        respective getter functions to allow for overwriting
        """
        if item in ["additionalProperties", "category", "description", "id", "links", "namespace", "nodeTerms",
                    "preferred", "program", "project", "properties", "required", "submittable", "systemProperties",
                    "title", "type", "uniqueKeys", "validators"]:
            if hasattr(self, "get_%s" % item) and callable(func := getattr(self, "get_%s" % item)):
                return func()
        else:
            return super().__getattribute__(item)

    def __setattr__(self, key, value):
        """
        Python magic in progress. this will redirect specific property access to
        setter functions to allow for overrides
        """
        if key in ["additionalProperties", "category", "description", "id", "links", "namespace", "nodeTerms",
                   "preferred", "program", "project", "properties", "required", "submittable", "systemProperties",
                   "title", "type", "uniqueKeys", "validators"]:
            if hasattr(self, "set_%s" % key) and callable(func := getattr(self, "set_%s" % key)):
                func(value)
        else:
            super().__setattr__(key, value)

    def get_additionalProperties(self):
        return self.data["additionalProperties"]

    def set_additionalProperties(self, value):
        self.data["additionalProperties"] = value

    def get_category(self):
        """wrap the data into a CATEGORY if we can"""
        raw_value = self.data["category"]
        if raw_value in Gen3Object.CATEGORY._value2member_map_:
            return Gen3Object.CATEGORY._value2member_map_[self.data["category"]]
        else:
            return raw_value

    def set_category(self, value):
        """unwrap the data if we can"""
        if isinstance(value, Gen3Object.CATEGORY):
            self.data["category"] = value.value
        else:
            self.data["category"] = value

    def get_description(self):
        return self.data["description"]

    def set_description(self, value):
        self.data["description"] = value

    def get_id(self):
        return self.data["id"]

    def set_id(self, value):
        self.data["id"] = value

    def get_links(self):
        links = self.data["links"]
        return [Gen3LinkGroup.from_dict(i) if Gen3LinkGroup.is_link_group(i) else Gen3Link.from_dict(i) for i in links]

    def set_links(self, value: List[Gen3WrapObject]):
        self.data["links"] = [i.get_data() for i in value]

    def get_namespace(self):
        return self.data["namespace"]

    def set_namespace(self, value):
        self.data["namespace"] = value

    def get_nodeTerms(self):
        return self.data["nodeTerms"]

    def set_nodeTerms(self, value):
        self.data["nodeTerms"] = value

    def get_preferred(self):
        return self.data["preferred"]

    def set_preferred(self, value):
        self.data["preferred"] = value

    def add_preferred(self, field_name):
        if "preferred" not in self.data:
            self.preferred = [field_name]
        else:
            self.preferred.append(field_name)

    def get_program(self):
        return self.data["program"]

    def set_program(self, value):
        self.data["program"] = value

    def get_project(self):
        return self.data["project"]

    def set_project(self, value):
        self.data["project"] = value

    def get_properties(self):
        return self.data["properties"]

    def set_properties(self, value):
        self.data["properties"] = value

    def add_property(self, prop: Gen3Property):
        if "properties" not in self.data:
            self.data["properties"] = {}
        self.data["properties"][prop.get_name()] = prop.get_data()

    def get_required(self):
        return self.data["required"]

    def set_required(self, value):
        self.data["required"] = value

    def add_required(self, value):
        if "required" not in self.data:
            self.required = [value]
        else:
            self.required.append(value)

    def get_submittable(self):
        return self.data["submittable"]

    def set_submittable(self, value):
        self.data["submittable"] = value

    def get_systemProperties(self):
        return self.data["systemProperties"]

    def set_systemProperties(self, value):
        self.data["systemProperties"] = value

    def get_title(self):
        return self.data["title"]

    def set_title(self, value):
        self.data["title"] = value

    def get_type(self):
        return self.data["type"]

    def get_uniqueKeys(self):
        return self.data["uniqueKeys"]

    def set_uniqueKeys(self, value):
        self.data["uniqueKeys"] = value

    def get_validators(self):
        return self.data["validators"]

    def set_validators(self, value):
        self.data["validators"] = value

    def get_references(self):
        """
        get all the references this object points to
        :return:
        """
        return self._get_ref_recurse(self.data)

    def get_data(self):
        """return the data dictionary representation of this Gen3Object"""
        return self.data

    def _get_ref_recurse(self, dat):
        """
        returse through a data dictionary and get all references
        :param dat: dictionary
        :return: list of Gen3Context
        """
        retval = []
        for key in dat:
            if key == "$ref":
                filename, path = Gen3Context.parse_id(dat[key])
                if filename == '':
                    filename = self.filename
                retval.append(Gen3Context(filename, path))
            elif isinstance(dat[key], dict):
                retval.extend(self._get_ref_recurse(dat[key]))
        return retval


class Gen3Link(Gen3WrapObject):
    class MULTIPLICITY(Enum):
        ONE_TO_ONE   = 'one_to_one'
        ONE_TO_MANY  = 'one_to_many'
        MANY_TO_ONE  = 'many_to_one'
        MANY_TO_MANY = 'many_to_many'

    def __init__(self,name: str, backref_name: str, label: str, target_type: str, multiplicity: MULTIPLICITY, required: bool):
        self.data = {"name":name,
                     "backref": backref_name,
                     "label": label,
                     "target_type": target_type,
                     "multiplicity": multiplicity.value,
                     "required:": required}

    @classmethod
    def from_dict(cls,data: dict):
        return cls(data["name"],
                   data["backref"],
                   data["label"],
                   data["target_type"],
                   Gen3Link.MULTIPLICITY._value2member_map_[data["multiplicity"]],
                   data["required"])

    def __getattribute__(self, item):
        """
        Python magic in progress. this will redirect all property accesses to the
        respective getter functions to allow for overwriting
        """
        if item in ["name","backref","label","target_type","multiplicity","required"]:
            if hasattr(self, "get_%s" % item) and callable(func := getattr(self, "get_%s" % item)):
                return func()
            elif item in self.data:
                self.data[item]
        else:
            return super().__getattribute__(item)

    def __setattr__(self, key, value):
        """
        Python magic in progress. this will redirect specific property access to
        setter functions to allow for overrides
        """
        if key in ["name","backref","label","target_type","multiplicity","required"]:
            if hasattr(self, "set_%s" % key) and callable(func := getattr(self, "set_%s" % key)):
                func(value)
            elif key in self.data:
                self.data[key] = value
        else:
            super().__setattr__(key, value)

    def get_multiplicity(self):
        return Gen3Link.MULTIPLICITY._value2member_map_[self.data["multiplicity"]]

    def set_multiplicity(self, mult: MULTIPLICITY):
        self.data["multiplicity"] = mult.value

    def get_data(self):
        return self.data.copy()


class Gen3LinkGroup(Gen3WrapObject):
    def __init__(self, links: List[Gen3Link] = [], exclusive = False, required= True):
        self.data = {"exclusive": exclusive, "required": required}
        self.links = links

    def get_links(self):
        return self.links

    def add_link(self, link: Gen3Link):
        self.links.append(link)

    def remove_link(self, link: Gen3Link):
        self.links.remove(link)

    @classmethod
    def from_dict(cls, data: dict):
        exclusive= data["exclusive"]
        required = True
        if "required" in data:
            required = data["required"]

        links = [Gen3Link.from_dict(i) for i in data["subgroup"]]
        return cls(links,exclusive,required)

    @staticmethod
    def is_link_group(data):
        return "subgroup" in data

    def get_data(self):
        self.data["subgroup"] = [l.get_data() for l in self.links]
        return self.data.copy()


class ConfigBundle:
    """
    A config bundle representing a data dictionary
    """

    def __init__(self, folder):
        self.folder = folder
        self.objects = {}
        self.definitions = {}
        self.vars = []
        self.referenced = []
        for file in glob.glob(os.path.join(folder, "*.yaml")):
            with open(file, "r") as stream:
                file = os.path.basename(file)
                data = yaml.safe_load(stream)
                if file.startswith("_"):
                    self.definitions[file] = data
                else:
                    self.objects[file] = Gen3Object(file, data)

                ctxt = Gen3Context(file, [])
                self._add_context_recurse(ctxt, data)

    def dump(self, folder):
        """
        dump the configuration bundle into a folder for the schema compiler

        :param folder: str
                the folder to dump the schema into. it is up to the implementer to ensure the folder is empty
        :return:
        """
        for file in self.definitions:
            with open(os.path.join(folder, file), "w") as stream:
                yaml.safe_dump(self.definitions[file], stream)

        for file in self.objects:
            with open(os.path.join(folder, file), "w") as stream:
                yaml.safe_dump(self.objects[file].get_data(), stream)

    def _remove_unneeded_refs(self):
        """
        delete all definitions in _terms and _definitions that are not referenced.
        :return:
        """
        for file in self.definitions:
            if file == "_settings.yaml":
                """_settings.yaml is protected"""
                continue
            marked_for_deletion = []
            for elem in self.definitions[file]:
                if elem == "id":
                    """id is protected"""
                    continue
                ctxt = Gen3Context(file, [elem])
                if ctxt not in self.referenced:
                    marked_for_deletion.append(elem)
            for elem in marked_for_deletion:
                del self.definitions[file][elem]

    def _find_by_context(self, ctxt: Gen3Context):
        """
        find a term by context.
        :param ctxt: context
        :return: a term
        """
        term: Gen3Term
        for term in self.vars:
            if term.context.__repr__() == ctxt.__repr__():
                return term
        raise KeyError()

    def _find_all_children(self, ctxt: Gen3Context):
        """
        return all terms defined beneath a context
        :param ctxt:
        :return:
        """
        term: Gen3Term
        retv = []
        for term in self.vars:
            if ctxt.__repr__() in term.__repr__():
                retv.append(term)
        return term

    def _add_context_recurse(self, context: Gen3Context, item: dict):
        for elem in item:
            if elem == "$ref":
                filename, path = Gen3Context.parse_id(item[elem])
                if filename == "":
                    filename = context.filename
                ref = Gen3Context(filename, path)
                if ref not in self.referenced:
                    self.referenced.append(ref)
            ctxt = context.get_subcontext(elem)
            if isinstance(item[elem], dict):
                self._add_context_recurse(ctxt, item[elem])
            else:
                self.vars.append(Gen3Term(item[elem], ctxt))
