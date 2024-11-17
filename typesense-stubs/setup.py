from setuptools import find_packages, setup

setup(
    name="typesense-stubs",
    version="0.1",
    description="Type stubs for the Typesense library",
    author="Arstanbek Usenov",
    author_email="arstan@globalify.xyz",
    url="https://github.com/Barnacle322/typesense-stubs",
    packages=find_packages(),
    install_requires=[
        "typesense",
    ],
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
)
