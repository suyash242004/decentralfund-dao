#!/usr/bin/env python3
"""
DecentralFund DAO - Setup Configuration
Package installation and development setup
"""

from setuptools import setup, find_packages
import os

# Read README file
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

# Package metadata
setup(
    name="decentralfund-dao",
    version="1.0.0",
    author="DecentralFund DAO Team",
    author_email="dev@decentralfund.dao",
    description="World's First Decentralized Autonomous Mutual Fund",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/decentralfund/dao",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Intended Audience :: Developers",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "black>=23.11.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
            "pre-commit>=3.5.0",
        ],
        "docs": [
            "sphinx>=7.2.6",
            "sphinx-rtd-theme>=1.3.0",
            "sphinx-autodoc-typehints>=1.25.2",
        ],
        "blockchain": [
            "brownie-eth>=1.20.0",
            "py-solc-x>=1.12.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "decentralfund=run:main",
            "decentralfund-api=backend.app:main",
            "decentralfund-worker=backend.tasks:main",
            "decentralfund-migrate=scripts.migrate_db:main",
            "decentralfund-deploy=scripts.deploy_contracts:main",
        ],
    },
    package_data={
        "backend": ["*.sql", "*.json"],
        "frontend": ["*.py", "*.css", "*.js"],
        "contracts": ["*.sol", "*.json"],
        "scripts": ["*.py", "*.sql"],
    },
    include_package_data=True,
    zip_safe=False,
    keywords=[
        "defi",
        "dao",
        "mutual-fund",
        "blockchain",
        "cryptocurrency",
        "investment",
        "portfolio",
        "governance",
        "sip",
        "fintech"
    ],
    project_urls={
        "Bug Reports": "https://github.com/decentralfund/dao/issues",
        "Source": "https://github.com/decentralfund/dao",
        "Documentation": "https://docs.decentralfund.dao",
        "Discord": "https://discord.gg/decentralfund",
        "Website": "https://decentralfund.dao",
    },
)