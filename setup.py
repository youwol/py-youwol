from pathlib import Path

from setuptools import setup, find_packages

# The directory containing this file
here = Path(__file__).parent

# The text of the README file
README = (Path(__file__).parent / "README.md").read_text()

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
    install_requires=[
        "aiohttp==3.8.1",
        "aiostream==0.4.4",
        "appdirs==1.4.4",
        "async-generator==1.10",
        "Brotli==1.0.9",
        "colorama==0.4.4",
        "cowpy==1.1.4",
        "fastapi==0.71.0",
        "Pillow==9.0.0",
        "python-multipart==0.0.5",
        "uvicorn==0.16.0",
        "watchgod==0.7",
        "websockets==10.1",
        "pyyaml==6.0",
        "kubernetes==21.7.0",
        "kubernetes_asyncio==19.15.0",
        "psutil==5.9.0",
        # Frozen indirect dependencies
        "aiosignal==1.2.0",
        "anyio==3.5.0",
        "asgiref==3.4.1",
        "async-timeout==4.0.2",
        "attrs==21.4.0",
        "charset-normalizer==2.0.10",
        "click==8.0.3",
        "frozenlist==1.2.0",
        "h11==0.12.0",
        "idna==3.3",
        "multidict==5.2.0",
        "pydantic==1.9.0",
        "six==1.16.0",
        "sniffio==1.2.0",
        "starlette==0.17.1",
        "typing_extensions==4.0.1",
        "yarl==1.7.2",
    ],
    entry_points={
        'console_scripts': ['youwol=youwol.main:main']
        }
    )
