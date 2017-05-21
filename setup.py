try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

version = '0.1.0'

install_requires = open('requirements.txt').read().strip().split()
setup(
    name='aioqueue',
    description='A Python Task Queue library using RabbitMQ (aioamqp) and asyncio',
    version=version,
    url='https://github.com/jjacobson93/aioqueue',
    author='Jeremy Jacobson',
    author_email='jjacobson93@gmail.com',
    packages=['aioqueue'],
    install_requires=install_requires,
    license='MIT'
)