from setuptools import setup, find_packages


setup(
    name='acs_student_attendance',
    version='1.0.3',
    url='https://github.com/petarmaric/acs_student_attendance',
    license='BSD',
    author='Petar Maric',
    author_email='petarmaric@uns.ac.rs',
    description='Console app and Python API for analyzing and reporting the '\
                'lab attendance of our ACS students',
    long_description=open('README.rst').read(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Topic :: Education',
        'Topic :: Utilities',
    ],
    platforms='any',
    packages=find_packages(),
    entry_points={
        'console_scripts': ['acs_student_attendance=acs_student_attendance.shell:main']
    },
    install_requires=open('requirements.txt').read().splitlines(),
)
