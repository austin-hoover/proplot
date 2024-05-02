from setuptools import find_packages, setup

if __name__ == '__main__':
    setup(
        maintainer='Luke Davis',
        maintainer_email='lukelbd@gmail.com',
        description='A succinct matplotlib wrapper for making beautiful graphics.',
        install_requires=['matplotlib>=3.0.0', 'numpy'],
        python_requires='>=3.6',
        packages=find_packages(),
        version='1.0.4',
        name='proplot',
        include_package_data=True,
    )
