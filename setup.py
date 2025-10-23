from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name                          = "puree-ui",
    version                       = "0.1.2",
    author                        = "Nicolai Prodromov",
    description                   = "XWZ Puree UI framework for Blender",
    long_description              = long_description,
    long_description_content_type = "text/markdown",
    url                           = "https://github.com/nicolaiprodromov/puree",
    packages                      = find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: User Interfaces",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
    install_requires=[
        "moderngl==5.12.0",
        "glcontext==3.0.0",
        "stretchable==1.1.7",
        "PyYAML==6.0.2",
        "typing-extensions==4.15.0",
        "attrs==25.3.0",
    ],
    package_data={
        "puree": [
            "shaders/*.glsl",
            "wheels/*.whl",
            "native_binaries/*.so",
            "native_binaries/*.pyd",
            "native_binaries/*.dylib",
        ],
    },
    include_package_data=True,
)
