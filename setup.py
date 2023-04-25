from setuptools import setup, find_packages

with open("README.md", "rt", encoding="utf-8") as file:
    long_description = file.read()

with open('requirements.txt') as f:
    install_requires = f.read().splitlines()

setup(
    name="gpt_bot",
    version="0.0.2",
    description="GPT Commandline interface bot",
    author="Hao Zhang",
    author_email="zh970205@mail.ustc.edu.cn",
    url="https://github.com/hzhangxyz/gpt-bot",
    packages=find_packages(),
    license="GPLv3",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=install_requires,
    python_requires=">=3.9",
)
