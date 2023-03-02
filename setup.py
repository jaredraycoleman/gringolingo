from setuptools import setup, find_packages

setup(
    name='gringolingo',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'openai',
        'tiktoken'
    ],
    # Add CLI script
    entry_points={
        'console_scripts': [
            'gringolingo = gringolingo.cli:main'
        ]
    }
)

