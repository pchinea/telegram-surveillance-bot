import setuptools


setuptools.setup(
    name="surveillance_bot",
    version="1.1",
    packages=['surveillance_bot'],
    install_requires=["python-telegram-bot>=13,<14", "opencv-python-headless>=4,<5"],
    python_requires='>=3.6, <3.10',
    entry_points={
        'console_scripts': [
            'surveillance_bot = surveillance_bot.main:main'
        ]
    },
    author="Pablo Chinea",
    author_email="khertz@gmail.com",
    description="Basic video surveillance system controlled "
                "through a telegram bot.",
    long_description=open("README.rst").read(),
    long_description_content_type="text/x-rst",
    license="GPL v3",
    url="https://github.com/pchinea/telegram-surveillance-bot",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Communications :: Chat",
        "Topic :: Internet",
        "Topic :: Multimedia :: Graphics :: Capture :: Digital Camera",
        "Topic :: Multimedia :: Video :: Capture",
        "Topic :: Security",
        "Topic :: Utilities"
    ]

)
