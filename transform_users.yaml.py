import ssl
import ldap3
import boto3
import io
import os

from users import *
import oyaml as yaml
from collections import OrderedDict
from ldap3 import Server, Connection, SAFE_SYNC, Tls
import argparse

RESOURCES = [OrderedDict({'name': 'sower'}),
              {'name': 'workspace', "description": "resource representing the workspace"},
              {'name': 'data_file', "description": "resource representing data uploads"},
              {'name': 'mds_gateway', 'description': 'commons /mds-admin'},
              {'name': 'services','subresources': [
                  {'name': 'sheepdog','subresources': [
                      {'name': 'submission','subresources': [
                          {'name': 'program'},
                          {'name': 'project'}
                      ]}
                  ]}
              ]},
              {'name': 'open'},
              {'name': 'programs','subresources': [
                  {'name': 'program1','subresources': [
                      {'name': 'projects','subresources': [
                          {'name': 'simulated'},
                          {'name': 'simulated2'},
                          {'name': 'AusDiab'},
                          {'name': 'FIELD'},
                          {'name': 'BioHEART-CT'},
                          {'name': 'test1'},
                          {'name': 'test2'},
                          {"name": "test3"}]}
                  ]},
                  {'name': 'jnkns','description': "Jenkins Testing Projects", 'subresources': [
                      {'name': 'projects','subresources': [
                          {'name': 'jenkins'}]}
                  ]}
              ]}
              ]

ROLES=[{'id': 'upload_files', 'permissions': [
    {'id': 'file_upload','action': {'service': 'fence', 'method': 'file_upload'}}
]},
       {'id': 'access_workspace','permissions': [
           {'id': 'workspace_access','action': {'service': 'jupyterhub', 'method': 'access'}}
       ]},
       {'id': 'administrate_sheepdog','description': 'CRUD access to programs and projects', 'permissions': [
           {'id': 'sheepdog_admin_action', 'action': {'service': 'sheepdog', 'method': '*'}}
       ]},
       {'id': 'access_metadata_service','permissions': [
           {'id': 'mds_access','action': {'service': 'mds_gateway', 'method': 'access'}}
       ]},
       {'id': 'administrate_indexd','description': 'full access to indexd API','permissions': [
           {'id': 'indexd_admin','action': {'service': 'indexd', 'method': '*'}}
       ]},
       {'id': 'admin','permissions': [
           {'id': 'admin', 'action': {'service': '*', 'method': '*'}}]},
       {'id': 'creator', 'permissions': [
           {'id': 'creator','action': {'service': '*', 'method': 'create'}}
       ]},
       {'id': 'reader','permissions': [
           {'id': 'reader','action': {'service': '*', 'method': 'read'}}
       ]},
       {'id': 'updater','permissions': [
           {'id': 'updater','action': {'service': '*', 'method': 'update'}}
       ]},
       {'id': 'deleter','permissions': [
           {'id': 'deleter','action': {'service': '*', 'method': 'delete'}}
       ]},
       {'id': 'storage_writer','permissions': [
           {'id': 'storage_creator','action': {'service': '*', 'method': 'write-storage'}}
       ]},
       {'id': 'storage_reader','permissions': [
           {'id': 'storage_reader','action': {'service': '*', 'method': 'read-storage'}}
       ]},
       {'id': 'access_sower','permissions': [
           {'id': 'sower_access','action': {'method': 'access', 'service': 'job'}}
       ]}
       ]

POLICIES=[{'id': 'access_workspace','description': 'be able to use workspace',
           'role_ids': ['access_workspace'],
           'resource_paths': ['/workspace']},
          {'id': 'data_upload','description': 'upload raw data files to S3',
           'role_ids': ['upload_files'],
           'resource_paths': ['/data_file']},
          {'id': 'program_project_admin','description': 'CRUD access to programs and projects',
           'role_ids': ['administrate_sheepdog'],
           'resource_paths': ['/services/sheepdog/submission/program', '/services/sheepdog/submission/project']},
          {'id': 'metadata_service_user','description': 'be able to use metadata service',
           'role_ids': ['access_metadata_service'],
           'resource_paths': ['/mds_gateway']},
          {'id': 'indexd_admin','description': 'full access to indexd API','role_ids':
              ['administrate_indexd'],
           'resource_paths': ['/programs']},
          {'id': 'open_data_reader',
           'role_ids': ['reader', 'storage_reader'],
           'resource_paths': ['/open']},
          {'id': 'sower_user','description': 'be able to user sower',
           'role_ids': ['access_sower'],
           'resource_paths': ['/sower']},
          {'id': 'all_programs_reader',
           'role_ids': ['reader', 'storage_reader'],
           'resource_paths': ['/programs']},
          {'id': 'jenkins',
           'role_ids': ['creator','reader','updater','deleter','storage_writer','storage_reader'],
           'resource_paths': ['/programs/jnkns', '/programs/jnkns/projects/jenkins']},
          {'id': 'program1',
           'role_ids': ['creator','reader','updater','deleter','storage_writer','storage_reader'],
           'resource_paths': [
               '/programs/program1'
           ]
           },
          {'id': 'program1_simulated',
           'role_ids': ['creator', 'reader', 'updater', 'deleter', 'storage_writer', 'storage_reader'],
           'resource_paths': [
               '/programs/program1/projects/simulated'
           ]
           },
          {'id': 'program1_simulated2',
           'role_ids': ['creator', 'reader', 'updater', 'deleter', 'storage_writer', 'storage_reader'],
           'resource_paths': [
               '/programs/program1/projects/simulated2',
            ]
           },
          {'id': 'program1_ausdiab',
           'role_ids': ['creator', 'reader', 'updater', 'deleter', 'storage_writer', 'storage_reader'],
           'resource_paths': [
               '/programs/program1/projects/AusDiab',
            ]
           },
          {'id': 'program1_field',
           'role_ids': ['creator', 'reader', 'updater', 'deleter', 'storage_writer', 'storage_reader'],
           'resource_paths': [
               '/programs/program1/projects/FIELD']
           },
          {'id': 'program1_bioheart_ct',
           'role_ids': ['creator', 'reader', 'updater', 'deleter', 'storage_writer', 'storage_reader'],
           'resource_paths': [
               '/programs/program1/projects/BioHEART-CT'
           ]
           },
          {'id': 'program1_test1',
           'role_ids': ['creator', 'reader', 'updater', 'deleter', 'storage_writer', 'storage_reader'],
           'resource_paths': [
               '/programs/program1/projects/test1'
           ]
           },
          {'id': 'program1_test2',
           'role_ids': ['creator', 'reader', 'updater', 'deleter', 'storage_writer', 'storage_reader'],
           'resource_paths': [
               '/programs/program1/projects/test2'
           ]
           },
          {'id': 'program1_test3',
           'role_ids': ['creator', 'reader', 'updater', 'deleter', 'storage_writer', 'storage_reader'],
           'resource_paths': [
               '/programs/program1/projects/test3'
           ]
           },
          ]

USERS=[('uwwint@gmail.com',
  {'tags': OrderedDict([('name', 'Uwe Winter')]), 'policies': []}),
 ('uwe@biocommons.org.au',
  {'tags': OrderedDict([('name', 'Uwe Winter')]), 'policies': []}),
 ('marion@biocommons.org.au',
  {'tags': OrderedDict([('name', 'Marion Shadbolt')]), 'policies': []}),
 ('bernie@biocommons.org.au',
  {'tags': OrderedDict([('name', 'Bernie Pope')]), 'policies': []}),
 ('tungvnguyen729@gmail.com',
  {'tags': OrderedDict([('name', 'Tung Nguyen')]), 'policies': []}),
 ('jeanyusyd@gmail.com',
  {'tags': OrderedDict([('name', 'Jean Yang')]), 'policies': []}),
 ('steven@biocommons.org.au',
  {'tags': OrderedDict([('name', 'Steven Manos')]), 'policies': []}),
 ('jeff@biocommons.org.au',
  {'tags': OrderedDict([('name', 'Jeff Christiansen')]), 'policies': []}),
 ('jess@biocommons.org.au',
  {'tags': OrderedDict([('name', 'Jess Holliday')]), 'policies': []}),
 ('christina@biocommons.org.au',
  {'tags': OrderedDict([('name', 'Christina Hall')]), 'policies': []}),
 ('melissa@biocommons.org.au',
  {'tags': OrderedDict([('name', 'Melissa Burke')]), 'policies': []}),
 ('andrew@biocommons.org.au',
  {'tags': OrderedDict([('name', 'Andrew Lonie')]), 'policies': []}),
 ('nigel@biocommons.org.au',
  {'tags': OrderedDict([('name', 'Nigel Ward')]), 'policies': []}),
 ('rhys@biocommons.org.au',
  {'tags': OrderedDict([('name', 'Rhys Francis')]), 'policies': []}),
 ('sarah@biocommons.org.au',
  {'tags': OrderedDict([('name', 'Sarah Nisbet')]), 'policies': []}),
 ('tiff@biocommons.org.au',
  {'tags': OrderedDict([('name', 'Tiff Nelson')]), 'policies': []}),
 ('johan@biocommons.org.au',
  {'tags': OrderedDict([('name', 'Johan Gustaffson')]), 'policies': []}),
 ('fiona@biocommons.org.au',
  {'tags': OrderedDict([('name', 'Fiona Kerr')]), 'policies': []}),
 ('pmeikle60@gmail.com',
  {'tags': OrderedDict([('name', 'Peter Meikle')]), 'policies': []}),
 ('farah@biocommons.org.au',
  {'tags': OrderedDict([('name', 'Farah Khan')]), 'policies': []})]

def create_yaml_from_template():
    uyml = UserYaml({})
    uyml.authz=Authz({},uyml)

    uyml.authz.anonymous_policies= []

    resources=list(map(lambda x: Resource(x,uyml),RESOURCES))
    uyml.authz.resources= resources
    roles=list(map(lambda x: Role(x,uyml),ROLES))
    uyml.authz.roles=roles
    policies=list(map(lambda x: Policy(x,uyml),POLICIES))
    uyml.authz.policies=policies
    users=dict((map(lambda x:(x[0],User(x[0],x[1],uyml)),USERS)))
    uyml.users=users
    uyml.authz.all_users_policies=list(filter(lambda x: x.get_uid() in ["program1_test1"],uyml.get_policies()))


    groups=[]
    group=Group({},uyml)
    group.name="data_uploader"
    group.policies=list(filter(lambda x: x.get_uid() in ["data_upload","program_project_admin","metadata_service_user"],uyml.get_policies()))
    group.users=list(filter(lambda x: x.get_uid() in ["uwe@biocommons.org.au","marion@biocommons.org.au"],uyml.get_users().values()))
    groups.append(group)

    group=Group({},uyml)
    group.name="indexd_admin"
    group.policies=list(filter(lambda x: x.get_uid() in ["indexd_admin"],uyml.get_policies()))
    group.users=list(filter(lambda x: x.get_uid() in ["uwe@biocommons.org.au","marion@biocommons.org.au"],uyml.get_users().values()))
    groups.append(group)

    group=Group({},uyml)
    group.name="program1_owners"
    group.policies=list(filter(lambda x: x.get_uid() in [
        "program1_simulated",
        "program1_simulated2",
        "program1_ausdiab",
        "program1_field",
        "program1_bioheart_ct",
        "program1_test1"],uyml.get_policies()))
    group.users=list(uyml.get_users().values())
    groups.append(group)

    group=Group({},uyml)
    group.name="workspace_user"
    group.policies=list(filter(lambda x: x.get_uid() in ["access_workspace","access_sower"],uyml.get_policies()))
    group.users=list(uyml.get_users().values())
    groups.append(group)

    for study in ["program1_simulated","program1_simulated2","program1_ausdiab","program1_field","program1_bioheart_ct","program1_test1"]:
        group = Group({}, uyml)
        group.name = study
        group.policies = list(filter(lambda x: x.get_uid() in [study], uyml.get_policies()))
        group.users=[]
        groups.append(group)

    uyml.authz.groups=groups
    return uyml

def add_ldap_users(uyml, server, user, password, search_dn):
    groups = uyml.authz.groups
    groupnames = list(map(lambda x: x.get_uid(),groups))
    glookup = dict(zip(groupnames,groups))

    tls = Tls(version=ssl.PROTOCOL_TLS, validate=ssl.CERT_REQUIRED)
    server = Server(server,port=389,use_ssl=True,tls=tls)
    print("Connecting to LDAP")
    conn = Connection(server, user, password,read_only=True, client_strategy=SAFE_SYNC, auto_bind=ldap3.AUTO_BIND_TLS_BEFORE_BIND)
    print("Connected, querying")
    status, result, response, _ = conn.search(search_dn, '(objectclass=voPerson)',attributes=ldap3.ALL_ATTRIBUTES)
    if not status:
        print(f"Query failsed: {result}")
        exit(-1)
    for ldap_user in response:
        if "voPersonApplicationUID;app-gen3" not in ldap_user['raw_attributes']:
            continue
        name=ldap_user['raw_attributes']['cn'][0].decode("utf-8")
        uname=ldap_user['raw_attributes']['voPersonApplicationUID;app-gen3'][0].decode("utf-8")

        user = User(uname,{},uyml)
        user.tags={'name':name}
        uyml.add_user(user)

        for gname in ldap_user['raw_attributes']['isMemberOf']:
            gname=gname.decode("utf-8")
            if gname in glookup:
                u=glookup[gname].users
                u.append(user)
                glookup[gname].users = u

def upload_to_s3(uyml,bucket,target):
    content=yaml.dump(uyml.get_dict(),sort_keys=True)
    data = io.BytesIO(content.encode("UTF-8"))
    s3= boto3.client("s3")
    s3.upload_fileobj(data,bucket,target)

if __name__ == "__main__":
    parser = argparse.ArgumentParser("Transforms the groups on an LDAP server into group access in gen3")
    parser.add_argument('--ldap-server',type=str,action="store",default='ldap://ldap-test.cilogon.org', help="the ldap server where the groups are set")
    parser.add_argument('--ldap-search-dn',type=str,default='ou=people,o=CAD,o=CO,dc=biocommons,dc=org,dc=au',help="the DN on which the search is based")
    parser.add_argument('--s3-bucket',type=str,action='store',default='biocommons-gen3-user', help='the S3 bucket to which the data is uploaded')
    parser.add_argument('--targetfile',type=str,action='store',default='cad/users.yaml',help='the file the user yaml is uploaded to')

    args=parser.parse_args()
    args.ldap_password=os.environ.get("LDAP_PASSWORD")
    args.ldap_user=os.environ.get("LDAP_USER")

    if args.ldap_password == "" or args.ldap_password is None:
        print("In order to login into the LDAP server you need to define LDAP_PASSWORD as environment variable")
        exit(-1)
    if args.ldap_user == "" or args.ldap_user is None:
        print("In order to login into the LDAP server you need to define LDAP_USER as environment variable")
        exit(-1)

    print("Generating YAML from template")
    uyml = create_yaml_from_template()
    print("Adding user access based on LDAP groups")
    add_ldap_users(uyml,args.ldap_server,args.ldap_user,args.ldap_password,args.ldap_search_dn)
    print("Uploading generated user.yaml")
    upload_to_s3(uyml,args.s3_bucket,args.targetfile)