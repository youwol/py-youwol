from pathlib import Path

from setuptools import setup, find_packages

# The directory containing this file
here = Path(__file__).parent

# The text of the README file
README = (Path(__file__).parent / "README.md").read_text()

requirements = (Path(__file__).parent / "requirements/base.in").read_text().splitlines()

setup(
    name='youwol',
    python_requires='~=3.6',
    version='0.0.3-next',
    description="Local YouWol environment",
    author="G. Reinisch, J. Decharne",
    author_email="greinich@youwol.com, jdecharne@youwol.com",
    long_description=README,
    long_description_content_type="text/markdown",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
    ],
    packages=find_packages(include=[
        'youwol',
        'youwol_utils',
        'youwol_utils.**',
        'youwol_data',
        'youwol.**'
    ]),
    package_data={
        'youwol_data': ['databases.zip', 'remotes-info.json']
    },
    include_package_data=True,
    install_requires=requirements,
    entry_points={
        'console_scripts': ['youwol=youwol.main:main']
    }
)
