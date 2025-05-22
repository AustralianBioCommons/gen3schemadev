from setuptools import setup

with open('requirements.txt') as f:
    install_requires = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
   name='gen3schemadev',
   version='0.1.0',
   description='An object mapper for Gen3 Schemas',
   author='Joshua Harris, Uwe Winter, Marion Shadbolt',
   author_email='joshua@biocommons.org.au, uwe@biocommons.org.au, marion@biocommons.org.au',
   packages=['gen3schemadev'],  # same as name
   install_requires=install_requires
)
