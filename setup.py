from setuptools import setup

setup(
   name='gen3schemadev',
   version='0.01',
   description='An object mapper for Gen3 Schemas',
   author='Uwe Winter, Marion Shadbolt',
   author_email='uwe@biocommons.org.au, marion@biocommons.org.au',
   packages=['gen3schemadev'],  #same as name
   install_requires=["gen3","argparse","numpy","setuptools","PyYAML","pandas","openpyxl","oyaml","networkx","matplotlib","ete3","dictionaryutils","numpy","boto3","ldap3"], #external packages as dependencies
)