"""Setup configuration for Trends.Earth API UI."""

from setuptools import find_packages, setup

with open("README.md", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="trendsearth-api-ui",
    version="0.1.0",
    author="Alex Zvoleff",
    author_email="azvoleff@conservation.org",
    description="A Dash app for viewing and managing the Trends.Earth GEF API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/azvoleff/trends.earth-api-ui",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-mock>=3.0",
            "pytest-cov>=3.0",
            "ruff>=0.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "trendsearth-api-ui=trendsearth_ui.app:main",
        ],
    },
    include_package_data=True,
    package_data={
        "trendsearth_ui": ["*.svg"],
    },
)
