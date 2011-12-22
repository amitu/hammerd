try:
        from ez_setup import use_setuptools
except ImportError:
        pass
else:
        use_setuptools()

from setuptools import setup

setup(
    name = "hammerd",
    version = "0.1.1",
    url = 'http://www.hammerd.org/',
    license = 'BSD',
    description = "HammerD Service and Helper libs",
    author = 'Amit Upadhyay',
    author_email = "upadhyay@gmail.com",
    py_modules = ["hammer", "hammerlib"],
    install_requires = ['amitu-zutils', "eventlet", "argparse"],
    entry_points={
        'console_scripts': [
            'hammerd = hammer:debug_main',
        ]
    },
)
