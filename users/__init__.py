import yaml
import inspect

class YamlObjectMapper:
    def __init__(self,data, context):
        self.data = data
        self.context = context
        for key in data:
            if key not in self.__class__.fields:
                print(f"Class {self.__class__.__name__} does not have field {key} defined, but it is contained in data dict")

    def __getattr__(self, item):
        if item in self.__class__.fields:
            obj = self.__class__.fields[item]
            if inspect.isclass(obj) and issubclass(obj,YamlObjectMapper):
                return obj(self.data.get(item,{}), self.context)
            elif isinstance(obj, CollectionOfYamlObjects):
                return obj.convert_from_dict(self.data.get(item,[]), self.context)
            elif isinstance(obj, ListResolver):
                return obj.list_to_items(self.context,self.data[item])
            else:
                return self.data.get(item,obj())
        else:
            return super().__getattr__(item)

    def __setattr__(self, key, value):
        if key in self.__class__.fields:
            obj = self.__class__.fields[key]
            if value is None:
                val = None
            elif inspect.isclass(obj) and issubclass(obj,YamlObjectMapper):
                val = value.get_dict()
            elif isinstance(obj, CollectionOfYamlObjects):
                val = obj.convert_to_dict(value)
            elif isinstance(obj, ListResolver):
                val = obj.items_to_list(value)
            elif value is None or isinstance(value,obj):
                val = value
            else:
                raise NotImplemented
            try:
                self.data[key] = val
            except AttributeError:
                pass
        else:
            super().__setattr__(key,value)

    def __str__(self):
        return yaml.dump(self.data)

    def __repr__(self):
        return self.__str__()

    def get_dict(self):
        return self.data

    def get_uid(self):
        return self.id


class ListResolver:
    def __init__(self, obj):
        self.obj = obj

    def list_to_items(self,context,l):
        return context.resolve(self.obj,l)

    def items_to_list(self, l):
        return [k.get_uid() for k in l]


class CollectionOfYamlObjects:
    def __init__(self,obj):
        self.obj = obj

    def convert_to_dict(self, l):
        raise NotImplemented()

    def convert_from_dict(self, l, context):
        raise NotImplemented()


class ListOfYamlObjects(CollectionOfYamlObjects):
    def convert_to_dict(self,l: list):
        if l is None:
            l = []
        return list(map(lambda x: x.get_dict(),l))

    def convert_from_dict(self, l: list,context):
        return list(map(lambda x: self.obj(x, context),l))


class DictOfYamlObjects(CollectionOfYamlObjects):
    def convert_to_dict(self,l: dict):
        if l is None:
            return dict()
        retv = {}
        for k in l:
            retv[k] = l[k].get_dict()
        return retv

    def convert_from_dict(self, l: dict, context):
        retv = {}
        for i in l:
            retv[i] = self.obj(i,l[i],context)
        return retv

class Action(YamlObjectMapper):
    fields = {"service": str, "method": str}

    def __init__(self,data,context):
        self.service = None
        self.method = None
        super().__init__(data,context)


class Permission(YamlObjectMapper):
    fields = {"id": str, "action": Action}

    def __init__(self,data,context):
        self.id = None
        self.action = None
        super().__init__(data,context)


class Role(YamlObjectMapper):
    fields = {"id": str, "permissions": ListOfYamlObjects(Permission)}

    def __init__(self,data,context):
        self.id = None
        self.permissions = None
        super().__init__(data,context)


class Resource(YamlObjectMapper):
    fields = {"name": str, "description": str}

    def __init__(self,data, context):
        if "subresources" not in Resource.fields:
            Resource.fields["subresources"] = ListOfYamlObjects(Resource)
        self.name = None
        self.description = None
        self.subresources = None
        super().__init__(data, context)

    def get_uid(self):
        return self.name

    def get_resources(self):
        return self.subresources

    def get_resource(self, name):
        f = list(filter(lambda x: x.get_uid() == name, self.get_resources()))
        if len(f) ==1:
            return f[0]
        return KeyError(name)


class Policy(YamlObjectMapper):
    fields = {"id": str, "description": str, "resource_paths": ListResolver(Resource), "role_ids": list}

    def __init__(self, data: dict,context):
        self.resource_paths = None
        self.description = None
        self.role_ids = None
        self.id = None
        super().__init__(data,context)

    @staticmethod
    def from_yaml_dict(yamldict: dict):
        retv = []
        for pol in yamldict:
            retv.append(Policy(pol))
        return retv


class KeyedYamlObjectMapper(YamlObjectMapper):
    def __init__(self,id: str,data: dict,context):
        self.id = id
        super().__init__(data,context)

    def __str__(self):
        d = {self.id: self.data}
        return yaml.dump(d)


class User(KeyedYamlObjectMapper):
    fields = {"policies": ListResolver(Policy), "tags": list}

    def __init__(self,id: str,data: dict, context):
        self.policies = None
        self.tags = None
        super().__init__(id,data, context)


class Client(KeyedYamlObjectMapper):
    fields = {"policies": list}

    def __init__(self, id: str, data: dict,context):
        self.policies = None
        super().__init__(id,data, context)


class Group(YamlObjectMapper):
    fields = {"name": str, "policies": ListResolver(Policy), "users": ListResolver(User) }

    def __init__(self,data, context):
        self.name = None
        self.policies = None
        self.users = None
        super().__init__(data, context)

    def get_uid(self):
        return self.name

class Authz(YamlObjectMapper):
    fields = {"anonymous_policies": ListResolver(Policy),
              "all_users_policies": ListResolver(User),
              "groups": ListOfYamlObjects(Group),
              "resources": ListOfYamlObjects(Resource),
              "policies": ListOfYamlObjects(Policy),
              "roles": ListOfYamlObjects(Role) }

    def __init__(self, data, context):
        self.anonymous_policies = None
        self.all_users_policies = None
        self.groups = None
        self.resources = None
        self.policies = None
        self.roles = None
        super().__init__(data, context)


class UserYaml(YamlObjectMapper):
    fields= {"authz": Authz, "clients": DictOfYamlObjects(Client), "users": DictOfYamlObjects(User)}

    def __init__(self,data):
        self.authz = None
        self.clients = None
        self.users = None
        super().__init__(data, self)

    def resolve(self,obj,l):
        objs = None

        if obj == Policy:
            objs = self.get_policies()
        if obj == User:
            objs = self.get_users().values()
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


    def get_policies(self):
        return  self.authz.policies

    def get_policy(self,name):
        f = list(filter(lambda x: x.get_uid() == name, self.get_policies()))
        if len(f) == 1:
            return f[0]
        else:
            raise KeyError(name)

    def add_policy(self,policy):
        p = self.get_policies()
        p.append(policy)
        self.authz.policies = p

    def remove_policy(self, policy):
        self.authz.policies = list(filter(lambda x: x.get_uid() != policy.get_uid(), self.get_policies()))

    def get_roles(self):
        return self.authz.roles

    def get_role(self,name):
        f = list(filter(lambda x: x.get_uid() == name, self.get_roles() ))
        if len(f) == 1:
            return f[0]
        else:
            raise KeyError(name)

    def add_role(self, role: Role):
        r = self.get_roles()
        r.append(role)
        self.auth.roles=r

    def remove_role(self, role: Role):
        self.authz.roles = list(filter(lambda x: x.get_uid() != role.get_uid(),self.get_roles()))

    def get_groups(self):
        return self.authz.groups

    def get_group(self,name):
        f = list(filter(lambda x: x.get_uid() == name, self.get_groups()))
        if len(f) == 1:
            return f[0]
        else:
            raise KeyError(name)

    def add_group(self,g: Group):
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
        self.users=u

    def get_resources(self):
        return self.authz.resources

    def get_resource(self, name):
        f = list(filter(lambda x: x.get_uid() == name, self.authz.resources))
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
