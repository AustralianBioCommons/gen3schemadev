import oyaml as yaml
import inspect
from functools import reduce
from collections import OrderedDict


class YamlObjectMapper:
    """
    Base class for all YamlObjects created within the context
    of a file. Context will be self on the root object and all objects under that point to root in order to be able resolve links

    One instance of his encapsulate the YML of one object as provided in a data dict. the contents
    of the data dict will then be exposed as attributes on the object as configured in the static variable *fields* defined on the class.
    i.e. one subclass is User, which maps "tags" to a dict, roles to a list of Roles.
    """

    def __init__(self, data: dict, context: 'YamlObjectMapper'):
        self.data = data
        self.drep = OrderedDict()
        self.context = context
        for key in data:
            if key not in self.__class__.fields:
                print(f"Class {self.__class__.__name__} does not have field {key} defined, but it is contained in data dict")

    def __getattr__(self, attribute_name):
        """
        maps an attribute defined in static class variable *field* onto variables

        :param attribute_name:
        :return:
        """
        if attribute_name in self.__class__.fields:
            obj = self.__class__.fields[attribute_name]
            if attribute_name in self.drep:
                retv = self.drep[attribute_name]
            elif inspect.isclass(obj) and issubclass(obj, YamlObjectMapper):
                retv = obj(self.data.get(attribute_name, OrderedDict()), self.context)
            elif isinstance(obj, CollectionOfYamlObjects):
                retv = obj.convert_from_dict(self.data.get(attribute_name, []), self.context)
            elif isinstance(obj, ListResolver):
                retv = obj.list_to_items(self.context, self.data[attribute_name])
            else:
                retv = self.data.get(attribute_name, obj())
            if attribute_name not in self.drep:
                self.drep[attribute_name] = retv
            return retv
        else:
            return super().__getattr__(attribute_name)

    def __setattr__(self, key, value):
        """
        set an attribute according to the configuration in static class variable *field*.
        :param key:
        :param value:
        :return:
        """
        if key in self.__class__.fields:
            obj = self.__class__.fields[key]
            if value is None:
                val = None
            elif inspect.isclass(obj) and issubclass(obj, YamlObjectMapper):
                val = value.get_dict()
            elif isinstance(obj, CollectionOfYamlObjects):
                val = obj.convert_to_dict(value)
            elif isinstance(obj, ListResolver):
                val = obj.items_to_list(value)
            elif value is None or isinstance(value, obj):
                val = value
            else:
                raise NotImplemented
            try:
                self.drep[key] = value
                self.data[key] = val
            except AttributeError:
                pass
        else:
            super().__setattr__(key, value)

    def __str__(self):
        return yaml.dump(self.data)

    def __repr__(self):
        return self.__str__()

    def get_dict(self) -> str:
        """
        returns the dict representation of this instance, so it can be dumped into the yaml

        :return:
        """
        for key in self.drep:
            val = self.drep[key]
            if isinstance(val, list):
                fobj = self.__class__.fields[key]
                if inspect.isclass(fobj) and issubclass(fobj, list):
                    self.data[key] = list(map(lambda x: x.get_dict() if isinstance(x, YamlObjectMapper) else x, val))
                elif isinstance(fobj, CollectionOfYamlObjects):
                    self.data[key] = fobj.convert_to_dict(val)
                elif isinstance(fobj, ListResolver):
                    self.data[key] = fobj.items_to_list(val)
            elif isinstance(val, dict):
                fobj = self.__class__.fields[key]
                retv = OrderedDict()
                if inspect.isclass(fobj) and issubclass(fobj, dict):
                    for k in val:
                        x = val[k]
                        retv[k] = x.get_dict() if isinstance(x, YamlObjectMapper) else x
                else:
                    retv = fobj.convert_to_dict(val)
                self.data[key] = retv
        return self.data

    def get_uid(self) -> str:
        """
        return the unique identifier that other objects use to link to this. Overridden in some subclasses, three different mechanisms are used:
        id attribute, name attribute and as a dict key (Users)
        :return:
        """
        return self.id

    def _resolve_attrs(self):
        """
        this function is called internally to finalize the construction of objects from data dicts.
        :return:
        """
        for k in self.data:
            dat = self.__getattr__(k)
            if isinstance(dat, list):
                list(map(lambda x: x._resolve_attrs() if isinstance(x, YamlObjectMapper) else None, dat))
            if isinstance(dat, dict):
                list(map(lambda x: x._resolve_attrs() if isinstance(x, YamlObjectMapper) else None, dat.values()))
            if isinstance(dat, YamlObjectMapper):
                dat._resolve_attrs()


class ListResolver:
    """
    Resolves to a list of object types, i.e. the YAML is a list of Roles, then ListResolver(Role) can convert the list
    ["role1","role2"] into a list of Role objects with those names as defined in authz.roles
    """
    def __init__(self, obj):
        self.obj = obj

    def list_to_items(self, context, l: list):
        return context.resolve(self.obj, l)

    def items_to_list(self, l: list):
        return [k.get_uid() for k in l]


class CollectionOfYamlObjects:
    """
    Base class for ListOfYamlObjects and DictOfYamlObjects.
    This is used to convert authz.roles to a list of Role objects, or users to a dict of User objects
    """
    def __init__(self, obj):
        self.obj = obj

    def convert_to_dict(self, dictionary: dict):
        raise NotImplemented()

    def convert_from_dict(self, dictionary: dict, context):
        raise NotImplemented()


class ListOfYamlObjects(CollectionOfYamlObjects):
    """
    See base class
    """
    def convert_to_dict(self, l: list):
        if l is None:
            l = []
        return list(map(lambda x: x.get_dict(), l))

    def convert_from_dict(self, l: list, context):
        return list(map(lambda x: self.obj(x, context), l))


class DictOfYamlObjects(CollectionOfYamlObjects):
    """
    See base class
    """
    def convert_to_dict(self, l: dict):
        if l is None:
            return dict()
        return_value = OrderedDict()
        for k in l:
            return_value[k] = l[k].get_dict()
        return return_value

    def convert_from_dict(self, l: dict, context):
        return_value = OrderedDict()
        for i in l:
            return_value[i] = self.obj(i, l[i], context)
        return return_value


class Action(YamlObjectMapper):
    """
    Object mapper for Action Object
    action has two attributes:
    service: str
    method: str
    """
    fields = OrderedDict(service=str, method=str)

    def __init__(self, data, context):
        self.service = None
        self.method = None
        super().__init__(data, context)


class Permission(YamlObjectMapper):
    """
    Object Mapper for Permission Object
    permission has two attributes:
    id: str
    action: Action
    """
    fields = OrderedDict(id=str, action=Action)

    def __init__(self, data, context):
        self.id = None
        self.action = None
        super().__init__(data, context)


class Role(YamlObjectMapper):
    """
    Object mapper for Role Object
    role has three attributes:
    id: str
    description: str
    permission: List[Permission]
    """
    fields = OrderedDict(id=str, description=str, permissions=ListOfYamlObjects(Permission))

    def __init__(self, data, context):
        self.id = None
        self.permissions = None
        super().__init__(data, context)


class Resource(YamlObjectMapper):
    """
    Object mapper for Resource Object
    Resource has three attributes:
    name: str
    description: str
    subresources: List[Resource] (set in the init function, due to python foo)
    """
    fields = OrderedDict(name=str, description=str)

    def __init__(self, data, context):
        if "subresources" not in Resource.fields:
            Resource.fields["subresources"] = ListOfYamlObjects(Resource)
        self.name = None
        self.description = None
        self.subresources = None
        self.parent = None
        super().__init__(data, context)

    def get_uid(self):
        """
        UID for a role is the subresource tree seperated by "/"
        :return:
        """
        return self.get_path()

    def _resolve_attrs(self):
        """hook into resolve atters and propagate the subresource tree, so that the eleements are aware of their parent."""
        super().__resolve_attrs()
        for sr in self.subresources:
            sr.parent = self

    def get_path(self):
        """get the path to the resource"""
        if self.parent == None:
            return ''
        else:
            return self.parent.get_path() + "/" + self.name

    def get_resources(self):
        """get sub resources wrapper, such that userYaml.get_resources and get resource work"""
        return self.subresources

    def get_resource(self, name):
        """
        get subresources with matching name
        :param name:
        :return:
        """
        f = list(filter(lambda x: x.name == name, self.get_resources()))
        if len(f) == 1:
            return f[0]
        return KeyError(name)


class Policy(YamlObjectMapper):
    """
    Policy Object Mapper. Policy has four attributes:
    id: str
    description: str
    resource_paths: List[Resource]
    role_ids: List[Roles by name]
    """
    fields = OrderedDict(id=str, description=str, resource_paths=ListResolver(Resource), role_ids=ListResolver(Role))

    def __init__(self, data: dict, context):
        self.resource_paths = None
        self.description = None
        self.role_ids = None
        self.id = None
        super().__init__(data, context)

    @staticmethod
    def from_yaml_dict(yamldict: dict):
        retv = []
        for pol in yamldict:
            retv.append(Policy(pol))
        return retv


class KeyedYamlObjectMapper(YamlObjectMapper):
    """
    Used to wrap users and client
    """
    def __init__(self, id: str, data: dict, context):
        self.id = id
        super().__init__(data, context)

    def __str__(self):
        d = OrderedDict({self.id: self.data})
        return yaml.dump(d)


class User(KeyedYamlObjectMapper):
    """
    User object mapper. User has two attributes:
    policies: LIst[Policy by name]
    tags: dict
    """
    fields = OrderedDict(policies=ListResolver(Policy), tags=dict)

    def __init__(self, id: str, data: dict, context):
        self.policies = None
        self.tags = None
        super().__init__(id, data, context)


class Client(KeyedYamlObjectMapper):
    """
    Client object Mapper
    Client has one attribute:
    fields: List[Policy by name]
    """
    fields = OrderedDict(policies=ListResolver(Policy))

    def __init__(self, id: str, data: dict, context):
        self.policies = None
        super().__init__(id, data, context)


class Group(YamlObjectMapper):
    """
    Group Object Mapper
    Group has three fields:
    name: str
    policies: List[Policies by name]
    users: List[Users by id]
    """
    fields = OrderedDict(name=str, policies=ListResolver(Policy), users=ListResolver(User))

    def __init__(self, data, context):
        self.name = None
        self.policies = None
        self.users = None
        super().__init__(data, context)

    def get_uid(self):
        """
        Group is referred to by name
        :return:
        """
        return self.name


class Authz(YamlObjectMapper):
    """
    Authz Object Mapper
    Authz has 6 fields:
    anonymous_policies: List[Policy by name]
    all_users_policies: List[Policy by name]
    groups: List[Group]
    resources: List[Resource]
    policies: List[Policy]
    roles: List[Role]
    """
    fields = OrderedDict(anonymous_policies=ListResolver(Policy),
                         all_users_policies=ListResolver(Policy),
                         groups=ListOfYamlObjects(Group),
                         resources=ListOfYamlObjects(Resource),
                         policies=ListOfYamlObjects(Policy),
                         roles=ListOfYamlObjects(Role))

    def __init__(self, data, context):
        self.anonymous_policies = None
        self.all_users_policies = None
        self.groups = None
        self.resources = None
        self.policies = None
        self.roles = None
        super().__init__(data, context)


class UserYaml(YamlObjectMapper):
    """
    Root Useryaml Object Mapper, This object wraps the whole user yaml and provides object access to the file.
    useryaml has three fields:
    authz: Authz
    clients: Dict(Client)
    users: Dict(User)
    """
    fields = OrderedDict(authz=Authz, clients=DictOfYamlObjects(Client), users=DictOfYamlObjects(User))

    def __init__(self, data):
        self.authz = None
        self.clients = None
        self.users = None
        super().__init__(data, self)
        self._resolve_attrs()

    def resolve(self, obj, l):
        objs = None

        if obj == Policy:
            objs = self.get_policies()
        if obj == User:
            objs = self.get_users().values()
        if obj == Role:
            objs = self.get_roles()
        if obj == Resource:
            retv = []
            for item in l:
                path = item.split("/")[1:]
                obj = self
                for elem in path:
                    obj = obj.get_resource(elem)
                retv.append(obj)
            return retv

        if objs is not None:
            return list(filter(lambda x: x.get_uid() in l, objs))
        raise NotImplemented

    def find_links_to(self, obj, base_obj):
        cls = base_obj.__class__
        mentions = []
        if cls == obj.__class__:
            if obj.get_uid() == base_obj.get_uid():
                mentions.append(obj)
        elif isinstance(base_obj, YamlObjectMapper):
            for field in cls.fields:
                target_class = cls.fields[field]
                target_obj = base_obj.__getattr__(field)
                if inspect.isclass(target_class):
                    if issubclass(target_class, obj.__class__) and target_obj.get_uid() == obj.get_uid():
                        mentions.append(target_obj)
                    if issubclass(target_class, YamlObjectMapper):
                        mentions.extend(self.find_links_to(obj, target_obj))
                elif isinstance(target_class, CollectionOfYamlObjects) or isinstance(target_class, ListResolver):
                    mentions.extend(self.find_links_to(obj, target_obj))
        elif isinstance(base_obj, list):
            mentions.extend(reduce(lambda x, y: x + y, map(lambda x: self.find_links_to(obj, x), base_obj), []))
        elif isinstance(base_obj, dict):
            mentions.extend(
                reduce(lambda x, y: x + y, map(lambda x: self.find_links_to(obj, x), base_obj.values()), []))
        return mentions

    def get_policies(self):
        return self.authz.policies

    def get_policy(self, name):
        f = list(filter(lambda x: x.get_uid() == name, self.get_policies()))
        if len(f) == 1:
            return f[0]
        else:
            raise KeyError(name)

    def add_policy(self, policy):
        p = self.get_policies()
        p.append(policy)
        self.authz.policies = p

    def remove_policy(self, policy):
        self.authz.policies = list(filter(lambda x: x.get_uid() != policy.get_uid(), self.get_policies()))

    def get_roles(self):
        return self.authz.roles

    def get_role(self, name):
        f = list(filter(lambda x: x.get_uid() == name, self.get_roles()))
        if len(f) == 1:
            return f[0]
        else:
            raise KeyError(name)

    def add_role(self, role: Role):
        r = self.get_roles()
        r.append(role)
        self.auth.roles = r

    def remove_role(self, role: Role):
        self.authz.roles = list(filter(lambda x: x.get_uid() != role.get_uid(), self.get_roles()))

    def get_groups(self):
        return self.authz.groups

    def get_group(self, name):
        f = list(filter(lambda x: x.get_uid() == name, self.get_groups()))
        if len(f) == 1:
            return f[0]
        else:
            raise KeyError(name)

    def add_group(self, g: Group):
        f = self.get_groups()
        f.append(g)
        self.authz.groups = f

    def remove_group(self, group: Group):
        self.authz.groups = list(filter(lambda x: x.get_uid() != group.get_uid(), self.get_groups()))

    def get_users(self):
        return self.users

    def get_user(self, name):
        return self.users[name]

    def add_user(self, user: User):
        u = self.get_users()
        u[user.id] = user
        self.users = u

    def remove_user(self, user: User):
        u = self.get_users()
        del u[user.id]
        self.users = u

    def get_resources(self):
        return self.authz.resources

    def get_resource(self, name):
        f = list(filter(lambda x: x.name == name, self.authz.resources))
        if len(f) == 1:
            return f[0]
        else:
            raise KeyError(name)

    def add_resource(self, resource):
        a = self.authz.resources
        a.append(resource)
        self.authz.resources = a

    def remove_resource(self, resource):
        self.authz.resources = list(filter(lambda x: x.get_uid() != resource.get_uid(), self.authz.resources))
