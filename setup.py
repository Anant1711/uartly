from setuptools import setup

setup(
    name="uartly",
    version="1.0",
    description="Advanced UART Serial Terminal",
    author="Anant Chauhan",
    author_email="anantchauhan010@gmail.com",
    license="MIT",
    py_modules=["uartly"],
    install_requires=[
        "pyserial",
        "customtkinter",
    ],
    entry_points={
        "console_scripts": [
            "uartly=uartly:main",
        ],
    },
    python_requires=">=3.8",
)
