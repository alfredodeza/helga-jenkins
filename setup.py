from setuptools import setup, find_packages

version = '0.0.5'

setup(name="helga-jenkins",
      version=version,
      description=('jenkins plugin for helga'),
      classifiers=['Development Status :: 4 - Beta',
                   'License :: OSI Approved :: MIT License',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python',
                   'Topic :: Software Development :: Libraries :: Python Modules',
                   ],
      keywords='irc bot jenkins',
      author='alfredo deza',
      author_email='contact [at] deza [dot] pe',
      url='https://github.com/alfredodeza/helga-jenkins',
      license='MIT',
      packages=find_packages(),
      install_requires=[
          'python-jenkins',
      ],
      entry_points = dict(
          helga_plugins = [
              'jenkins = helga_jenkins:helga_jenkins',
          ],
      ),
)
