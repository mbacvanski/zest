from setuptools import setup, find_packages

setup(
    name="zest",
    version="0.1.0",
    description="Object-oriented circuit graph wrapper for PySpice",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "pyspice",
        "networkx",
        "matplotlib"
    ],
    python_requires=">=3.7",
) 