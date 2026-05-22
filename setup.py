from setuptools import setup

setup(
    name="openai-unlimited",
    version="1.0.0",
    description="Free GPT-5 API — terminal agent, OpenAI API server, MCP server. No key, no login.",
    author="Singh-army",
    url="https://github.com/Singh-army/openai-unlimited",
    py_modules=["run"],
    python_requires=">=3.8",
    install_requires=[
        "httpx",
        "fastapi",
        "uvicorn[standard]",
        "mcp[cli]",
    ],
    entry_points={
        "console_scripts": [
            "unlimitedai=run:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
