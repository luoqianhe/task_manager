#!/usr/bin/env python3
"""
Setup script for Task Organizer
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="task-organizer",
    version="1.0.0",
    author="Task Organizer Team",
    author_email="", # Add your email here
    description="A modern, feature-rich task management application built with Python and PyQt6",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/task-organizer",  # Update with your GitHub URL
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Scheduling",
        "Topic :: Desktop Environment",
        "Environment :: X11 Applications :: Qt",
    ],
    python_requires=">=3.9",
    install_requires=read_requirements(),
    entry_points={
        "console_scripts": [
            "task-organizer=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["resources/icons/*"],
    },
)