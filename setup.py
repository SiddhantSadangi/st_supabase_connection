from pathlib import Path

import setuptools

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()


def get_version(rel_path):
    with open(rel_path, "r", encoding="UTF-8") as f:
        for line in f:
            if line.startswith("__version__"):
                delim = '"' if '"' in line else "'"
                return line.split(delim)[1]
    raise RuntimeError("Unable to find version string.")


setuptools.setup(
    name="st-supabase-connection",
    version=get_version("src/st_supabase_connection/__init__.py"),
    url="https://github.com/SiddhantSadangi/st_supabase_connection",
    author="Siddhant Sadangi",
    author_email="siddhant.sadangi@gmail.com",
    description="A Streamlit connection component for Supabase.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    project_urls={
        "Homepage": "https://github.com/SiddhantSadangi/st_supabase_connection",
        "Documentation": "https://github.com/SiddhantSadangi/st_supabase_connection/blob/main/README.md",
        "Support": "https://www.buymeacoffee.com/siddhantsadangi",
    },
    packages=setuptools.find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    classifiers=[
        "Environment :: Plugins",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: User Interfaces",
    ],
    keywords=["streamlit", "supabase", "connection", "integration"],
    python_requires=">=3.8",
    install_requires=["streamlit>=1.2", "supabase"],
)
