from setuptools import setup

setup(
   name='gen3schemadev',
   version='0.01',
   description='An object mapper for Gen3 Schemas',
   author='Uwe Winter',
   author_email='uwe@biocommons.org.au',
   packages=['gen3schemadev'],  #same as name
   install_requires=["setuptools~=58.5.3","PyYAML~=6.0","pandas~=1.3.5","openpyxl","oyaml~=1.0","networkx~=2.6.3","matplotlib","ete3","dictionaryutils~=3.0.0","numpy~=1.22.1"], #external packages as dependencies
)