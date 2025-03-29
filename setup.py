from setuptools import setup, find_packages

setup(
    name="gedcom-browser",
    version="0.1.0",
    description="A tool to browse GEDCOM 5.5.5 genealogical data files",
    author="Quentin",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'gedcom-browser=main:main',
        ],
    },
    install_requires=[],
    python_requires='>=3.7',
)