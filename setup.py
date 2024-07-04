#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
import subprocess

from setuptools import setup, find_packages
from setuptools.command.install import install as _install

from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

class install(_install):
    def run(self):
        subprocess.run(["ksc", "-t", "python", "--outdir", "acd/generated/", "--python-package", "acd.generated", "resources/templates/Dat/Dat.ksy"])
        subprocess.run(["ksc", "-t", "python", "--outdir", "acd/generated/comps/", "--python-package", "acd.generated.comps", "resources/templates/Comps/RxTag.ksy"])
        subprocess.run(
            ["ksc", "-t", "python", "--outdir", "acd/generated/comps/", "--python-package", "acd.generated.comps",
             "resources/templates/Comps/FAFA_Comps.ksy"])
        subprocess.run(
            ["ksc", "-t", "python", "--outdir", "acd/generated/sbregion/", "--python-package", "acd.generated.sbregion",
             "resources/templates/SbRegion/FAFA_SbRegion.ksy"])
        subprocess.run(
            ["ksc", "-t", "python", "--outdir", "acd/generated/comps/", "--python-package", "acd.generated.comps",
             "resources/templates/Comps/FDFD_Comps.ksy"])
        subprocess.run(
            ["ksc", "-t", "python", "--outdir", "acd/generated/comments/", "--python-package", "acd.generated.comments",
             "resources/templates/Comments/FAFA_Comments.ksy"])
        _install.run(self)
        print("--------------------------------------------------------------------")

setup(
    name="acd-tools",
    version="0.1a5",
    description="Rockwell ACD File Tools",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.8",
        "Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator",
    ],
    keywords="rockwell acd logix",
    url="https://github.com/hutcheb/acd",
    author="Ben Hutcheson",
    author_email="",
    license="Apache 2.0",
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=find_packages(include=["acd", "acd.*"]),
    setup_requires=[
        "wheel",
    ],
    install_requires=[
        "loguru",
        "kaitaistruct",
    ],
    extras_require={
        "dev": [
            "requires",
            "pytest-asyncio>=0.18.3",
            "pip-tools",
            "pre-commit>=2.6.0",
            "pytest-mock>=3.3.1",
            "mock>=4.0.2",
            "mypy>=0.942",
            "flake8>=4.0.1",
        ]
    },
    cmdclass={'install': install},
)
