import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="scrimage",
    version="0.0.1",
    author="Martin Fitzpatrick",
    author_email="martin.fitzpatrick@gmail.com",
    description="Convert SAM SCREEN$ to Image files, and vice versa.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mfitzp/scrimage",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.4',
    entry_points = {
        'console_scripts': [
            'sam2img=scrimage.commands.sam2img:main',
            'img2sam=scrimage.commands.img2sam:main',
        ],
    }
)