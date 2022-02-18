import oyaml as yaml
import inspect
from functools import reduce
from collections import OrderedDict



class YamlObjectMapper:
    def __init__(self,data, context):
        self.data = data
        self.drep = OrderedDict()
        self.context = context
        for key in data:
            if key not in self.__class__.fields:
                print(f"Class {self.__class__.__name__} does not have field {key} defined, but it is contained in data dict")

    def __getattr__(self, item):
        if item in self.__class__.fields:
            obj = self.__class__.fields[item]
            if item in self.drep:
                retv = self.drep[item]
            elif inspect.isclass(obj) and issubclass(obj,YamlObjectMapper):
                retv = obj(self.data.get(item,OrderedDict()), self.context)
            elif isinstance(obj, CollectionOfYamlObjects):
                retv = obj.convert_from_dict(self.data.get(item,[]), self.context)
            elif isinstance(obj, ListResolver):
                retv = obj.list_to_items(self.context,self.data[item])
            else:
                retv = self.data.get(item,obj())
            if item not in self.drep:
                self.drep[item] = retv
            return retv
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
                self.drep[key] = value
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
        for key in self.drep:
            val = self.drep[key]
            if isinstance(val,list):
                fobj = self.__class__.fields[key]
                if inspect.isclass(fobj) and issubclass(fobj,list):
                    self.data[key] = list(map(lambda x: x.get_dict() if isinstance(x,YamlObjectMapper) else x, val))
                elif isinstance(fobj, CollectionOfYamlObjects):
                    self.data[key] = fobj.convert_to_dict(val)
                elif isinstance(fobj, ListResolver):
                    self.data[key] = fobj.items_to_list(val)
            elif isinstance(val,dict):
                fobj = self.__class__.fields[key]
                retv=OrderedDict()
                if inspect.isclass(fobj) and issubclass(fobj, dict):
                    for k in val:
                        x = val[k]
                        retv[k] = x.get_dict() if isinstance(x,YamlObjectMapper) else x
                else:
                    retv = fobj.convert_to_dict(val)
                self.data[key] = retv
        return self.data

    def get_uid(self):
        return self.id

    def resolve_attrs(self):
        for k in self.data:
            dat = self.__getattr__(k)
            if isinstance(dat,list):
                list(map(lambda x: x.resolve_attrs() if isinstance(x,YamlObjectMapper) else None,dat))
            if isinstance(dat,dict):
                list(map(lambda x: x.resolve_attrs() if isinstance(x,YamlObjectMapper) else None, dat.values()))
            if isinstance(dat, YamlObjectMapper):
                dat.resolve_attrs()


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
        retv = OrderedDict()
        for k in l:
            retv[k] = l[k].get_dict()
        return retv

    def convert_from_dict(self, l: dict, context):
        retv = OrderedDict()
        for i in l:
            retv[i] = self.obj(i,l[i],context)
        return retv

class Action(YamlObjectMapper):
    fields = OrderedDict(service= str, method= str)

    def __init__(self,data,context):
        self.service = None
        self.method = None
        super().__init__(data,context)


class Permission(YamlObjectMapper):
    fields = OrderedDict(id= str, action= Action)

    def __init__(self,data,context):
        self.id = None
        self.action = None
        super().__init__(data,context)


class Role(YamlObjectMapper):
    fields = OrderedDict(id= str,description= str, permissions= ListOfYamlObjects(Permission))

    def __init__(self,data,context):
        self.id = None
        self.permissions = None
        super().__init__(data,context)


class Resource(YamlObjectMapper):
    fields = OrderedDict(name= str, description= str)

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
    fields = OrderedDict(id= str, description= str, resource_paths= ListResolver(Resource), role_ids= ListResolver(Role))

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
        d = OrderedDict({self.id: self.data})
        return yaml.dump(d)


class User(KeyedYamlObjectMapper):
    fields = OrderedDict(policies= ListResolver(Policy), tags= dict)

    def __init__(self,id: str,data: dict, context):
        self.policies = None
        self.tags = None
        super().__init__(id,data, context)


class Client(KeyedYamlObjectMapper):
    fields = OrderedDict(policies= ListResolver(Policy))

    def __init__(self, id: str, data: dict,context):
        self.policies = None
        super().__init__(id,data, context)


class Group(YamlObjectMapper):
    fields = OrderedDict(name= str, policies= ListResolver(Policy), users= ListResolver(User) )

    def __init__(self,data, context):
        self.name = None
        self.policies = None
        self.users = None
        super().__init__(data, context)

    def get_uid(self):
        return self.name

class Authz(YamlObjectMapper):
    fields = OrderedDict(anonymous_policies= ListResolver(Policy),
              all_users_policies= ListResolver(User),
              groups= ListOfYamlObjects(Group),
              resources= ListOfYamlObjects(Resource),
              policies= ListOfYamlObjects(Policy),
              roles= ListOfYamlObjects(Role) )

    def __init__(self, data, context):
        self.anonymous_policies = None
        self.all_users_policies = None
        self.groups = None
        self.resources = None
        self.policies = None
        self.roles = None
        super().__init__(data, context)


class UserYaml(YamlObjectMapper):
    fields= OrderedDict(authz= Authz, clients= DictOfYamlObjects(Client), users= DictOfYamlObjects(User))

    def __init__(self,data):
        self.authz = None
        self.clients = None
        self.users = None
        super().__init__(data, self)
        self.resolve_attrs()

    def resolve(self,obj,l):
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

    def find_links_to(self,obj,base_obj):
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
                    if issubclass(target_class,obj.__class__) and target_obj.get_uid() == obj.get_uid():
                        mentions.append(target_obj)
                    if issubclass(target_class,YamlObjectMapper):
                        mentions.extend(self.find_links_to(obj,target_obj))
                elif isinstance(target_class,CollectionOfYamlObjects) or isinstance(target_class,ListResolver):
                    mentions.extend(self.find_links_to(obj,target_obj))
        elif isinstance(base_obj, list):
            mentions.extend(reduce(lambda x,y: x+y,map(lambda x: self.find_links_to(obj,x),base_obj),[]))
        elif isinstance(base_obj, dict):
            mentions.extend(reduce(lambda x, y: x + y, map(lambda x: self.find_links_to(obj, x), base_obj.values()), []))
        return mentions

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
