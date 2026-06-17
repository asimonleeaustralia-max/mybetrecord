from setuptools import setup, find_packages

setup(
    name="betrecord-shared",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "fastapi>=0.110",
        "sqlalchemy>=2.0",
        "psycopg[binary]>=3.1",
        "pydantic[email]>=2.6",
        "bcrypt>=4.1",
        "pyjwt>=2.8",
    ],
)
