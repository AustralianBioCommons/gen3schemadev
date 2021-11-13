from setuptools import setup

setup(
   name='gen3schemadev',
   version='0.01',
   description='An object mapper for Gen3 Schemas',
   author='Uwe Winter',
   author_email='uwe@biocommons.org.au',
   packages=['gen3schemadev'],  #same as name
   install_requires=['PyYAML~=6.0'], #external packages as dependencies
)