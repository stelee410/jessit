from setuptools import setup, find_packages

setup(
    name="jessit",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "PyQt6>=6.5.0",
        "anthropic>=0.18.0",
        "openai>=1.0.0",
        "pyautogui>=0.9.54",
        "pydirectinput>=1.0.4",
        "uiautomation>=2.0.0",
        "pywin32>=306",
        "openpyxl>=3.1.2",
        "pandas>=2.1.0",
        "pyyaml>=6.0",
        "pydantic>=2.0.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "jessit=src.main:main",
        ],
    },
    python_requires=">=3.9",
)
