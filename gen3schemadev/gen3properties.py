from abc import abstractmethod


class Gen3WrapObject:
    @abstractmethod
    def get_data(self) -> dict:
        pass




class Gen3Property(Gen3WrapObject):
    def __init__(self, name, description=None, termdef=None, source=None, term_id=None, term_version=None):
        self.name = name
        self.data = {"description": description}
        self.set_definition(termdef, source, term_id, term_version)

    def get_name(self):
        return self.name

    def init_from_dict(self, d: dict):
        self.data = d.copy()
        if "description" not in self.data:
            self.set_description(None)
        if "termDef" not in self.data:
            self.set_definition()

    def set_name(self, name):
        self.name = name

    def remove_null(self):
        data_copy = self.data.copy()
        marked_for_deletion = []
        for key, value in data_copy.items():
            if not value:
                marked_for_deletion.append(key)
        for key in marked_for_deletion:
            del data_copy[key]
        return data_copy

    def get_data(self):
        return self.remove_null()

    def set_description(self, description):
        self.data["description"] = description

    def get_description(self):
        return self.data["description"]

    def set_definition(self, termdef=None, source=None, term_id=None, term_version=None):
        if not isinstance(term_version, str):
            term_version = str(term_version)
        self.data["termDef"] = [{"term": termdef, "source": source, "term_id": term_id, "term_version": term_version}]

    def get_definition(self):
        return self.data["termDef"]


class Gen3DatetimeProperty(Gen3Property):
    def __init__(self, name, description="", termdef=None, source=None, term_id=None, term_version=None):
        super().__init__(name, description, termdef, source, term_id, term_version)

    def get_data(self):
        return {"$ref": "_definitions.yaml#/datetime", "description": self.data["description"]}


class Gen3JsonProperty(Gen3Property):
    def __init__(self, name, typename, description="", termdef=None, source=None, term_id=None, term_version=None):
        super().__init__(name, description, termdef, source, term_id, term_version)
        self.type = typename
        self.data["type"] = typename

    def init_from_dict(self, d: dict):
        if "type" not in d or d["type"] != self.type:
            raise ValueError(d)
        else:
            super().init_from_dict(d)


class Gen3Number(Gen3JsonProperty):
    def __init__(self, name, description="", termdef=None, source=None, term_id=None, term_version=None):
        super().__init__(name, "number", description, termdef, source, term_id, term_version)

    def set_minimum(self, num):
        if num is None:
            del self.data["minimum"]
        else:
            self.data["minimum"] = num

    def get_minimum(self):
        return self.data["minimum"]

    def set_maximum(self, num):
        if num is None:
            del self.data["maximum"]
        else:
            self.data["maximum"] = num

    def get_maximum(self):
        return self.data["maximum"]


class Gen3Integer(Gen3JsonProperty):
    def __init__(self, name, description="", termdef=None, source=None, term_id=None, term_version=None):
        super().__init__(name, "integer", description, termdef, source, term_id, term_version)

    def set_minimum(self, num):
        if num is None:
            del self.data["minimum"]
        else:
            self.data["minimum"] = num

    def get_minimum(self):
        return self.data["minimum"]

    def set_maximum(self, num):
        if num is None:
            del self.data["maximum"]
        else:
            self.data["maximum"] = num

    def get_maximum(self):
        return self.data["maximum"]


class Gen3String(Gen3JsonProperty):
    def __init__(self, name, description="", pattern=None, termdef=None, source=None, term_id=None, term_version=None):
        super().__init__(name, "string", description, termdef, source, term_id, term_version)
        self.data["pattern"] = pattern


class Gen3Boolean(Gen3JsonProperty):
    def __init__(self, name, description="", termdef=None, source=None, term_id=None, term_version=None):
        super().__init__(name, "boolean", description, termdef, source, term_id, term_version)


class Gen3Enum(Gen3Property):
    def __init__(self, name, description="", termdef=None, source=None, term_id=None, term_version=None):
        super().__init__(name, description, termdef, source, term_id, term_version)
        self.data["enum"] = []
        self.data["enumDef"] = []

    def add_enum_option(self, name, source=None, term_id=None, version=None):
        if name not in self.data["enum"]:
            self.data["enum"].append(name)
            if source is not None or term_id is not None or version is not None:
                self.set_enum_term_def(name, source, term_id, version)
        else:
            raise ValueError(name)

    def get_enum_term_def(self, name):
        for enum_term_def in self.data['enumDef']:
            if enum_term_def["enumeration"] == name:
                return enum_term_def.copy()
        return None

    def get_values(self):
        return self.data['enum'].copy()

    def set_enum_term_def(self, name=None, source=None, term_id=None, version=None):
        found = False
        for enum_term_def in self.data['enumDef']:
            if enum_term_def["enumeration"] == name:
                enum_term_def["source"] = source
                enum_term_def["term_id"] = term_id
                enum_term_def["version"] = version
                found = True
                break
        if not found:
            self.data["enumDef"].append({
                "enumeration": name,
                "source": source,
                "term_id": term_id,
                "version": version
            })
