import os

from setuptools import setup

here = os.getcwd()

with open(os.path.join(here, "requirements.txt")) as f:
    requirements_lines = f.readlines()
install_requires = [r.strip() for r in requirements_lines]

setup(
    name="umitemplatedb",
    version="",
    packages=["tests", "umitemplatedb"],
    url="",
    license="",
    install_requires=install_requires,
    author="Samuel Letellier-Duchesne",
    author_email="samueld@mit.edu",
    description="Functions to import and query the UmiTemplate DataBase",
)
