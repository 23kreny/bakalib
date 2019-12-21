from setuptools import find_packages, setup

from bakalib import version

with open("README.md", "r", encoding="utf-8") as readme:
    long_description = readme.read()

setup(
    name="bakalib",
    version=version,
    author="kreny",
    author_email="kronerm9@gmail.com",
    description="A library for accessing the module data of Bakaláři school system easily",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/23kreny/bakalib",
    include_package_data=True,
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=["lxml", "requests", "xmltodict", "cachetools"],
)
