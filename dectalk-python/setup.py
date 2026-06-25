from setuptools import setup, find_packages

setup(
    name="dectalk",
    version="4.64.0",
    description="Python bindings for DECtalk text-to-speech engine (64-bit)",
    author="DECtalk Community",
    license="Custom",
    packages=["dectalk"],
    package_data={"dectalk": ["bin/*"]},
    python_requires=">=3.8",
    platforms=["win_amd64"],
    url="https://github.com/dectalk/dectalk",
)
