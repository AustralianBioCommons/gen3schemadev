import glob
import os
import oyaml as yaml
from .gen3object import Gen3Object, Gen3Context, Gen3LinkGroup, Gen3Link

import networkx as nx

class Gen3Term:
    """A term defined in a file within a context. A term is either list or string"""

    def __init__(self, value, context):
        self.value = value
        self.context = context

    def __repr__(self):
        return self.context.__repr__() + ": " + self.value


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
        if not os.path.isdir(folder):
            os.mkdir(folder)
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

    def getObjectByID(self, uid: str):
        for i in self.objects.values():
            if i.id == uid:
                return i
        raise KeyError(uid)

    def addObject(self, obj: Gen3Object):
        self.objects[obj.filename] = obj

    def getDependencyGraph(self):
        graph = nx.DiGraph()
        for obj in self.objects.values():
            to_obj = obj.id
            for link_element in obj.get_links():
                links = [link_element]
                if isinstance(link_element, Gen3LinkGroup):
                    links = link_element.get_links()
                for link in links:
                    from_obj = link.target_type
                    link_data = {}

                    if link.multiplicity == Gen3Link.MULTIPLICITY.MANY_TO_MANY or \
                            link.multiplicity == Gen3Link.MULTIPLICITY.ONE_TO_MANY:
                        link_data["MUL_FROM"] = "N"
                    else:
                        link_data["MUL_FROM"] = "1"

                    if link.multiplicity == Gen3Link.MULTIPLICITY.MANY_TO_ONE or \
                            link.multiplicity == Gen3Link.MULTIPLICITY.MANY_TO_MANY:
                        link_data["MUL_TO"] = "N"
                    else:
                        link_data["MUL_TO"] = "1"

                    link_data["label"] = link.label
                    link_data["name"] = link.backref
                    link_data["reverse_name"] = link.name
                    link_data["required"] = link.required

                    graph.add_edge(from_obj, to_obj, **link_data)
        return graph