# Compilation block
########################################################################################
import os
import sys
import fnmatch

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

from setuptools import find_packages, setup, Command
from setuptools.extension import Extension
from setuptools.command.sdist import sdist as _sdist
from setuptools.command.build_py import build_py as build_py_orig
from setuptools.command.install_lib import install_lib as _install_lib
try:
    from Cython.Build import cythonize, build_ext as _build_ext
except ImportError:
    has_cython = False
else:
    has_cython = True

try:
    from sphinx.setup_command import BuildDoc
    import sphinx  # noqa: F401
    has_sphinx = True
except ImportError:
    has_sphinx = False


def get_discription(file_path='README.rst', folder=os.getcwd()):
    with open("{}/{}".format(folder, file_path)) as readme:
        return readme.read()


def load_requirements(file_name, folder=os.getcwd()):
    with open(os.path.join(folder, file_name)) as req_file:
        return req_file.read().strip().split('\n')


def get_file_ext(ext):
    file_types = [".py", ".pyx", ".c", '.cpp'] if has_cython else [".c", '.cpp', ".py"]
    for ftype in file_types:
        fname = ext.replace(".", "/") + ftype
        if os.path.exists(fname):
            return fname
    return None


def listfiles(folder):
    for root, folders, files in os.walk(folder):
        for filename in folders + files:
            yield os.path.join(root, filename)


def clear_old_extentions(extensions_list):
    for filename in listfiles('vstutils'):
        _filename, _f_ext = os.path.splitext(filename)
        if os.path.isdir(_filename) or _f_ext not in ['.c', '.cpp']:
            continue
        has_py = (
            os.path.exists('{}.py'.format(_filename)) or
            os.path.exists('{}.pyx'.format(_filename))
        )

        if has_py and filename.replace('/', '.').replace(_f_ext, '') in extensions_list:
            print('Removing old extention [{}].'.format(filename))
            os.remove(filename)


def make_extensions(extensions_list):
    if not isinstance(extensions_list, list):
        raise Exception("Extension list should be `list`.")

    clear_old_extentions(extensions_list)

    extensions_dict = {}
    for ext in extensions_list:
        files = []
        module_name = ext
        if isinstance(ext, (list, tuple)):
            module_name = ext[0]
            for file_module in ext[1]:
                file_name = get_file_ext(file_module)
                files += [file_name] if file_name else []
        else:
            file_name = get_file_ext(ext)
            files += [file_name] if file_name else []
        if files:
            extensions_dict[module_name] = files

    ext_modules = list(
        Extension(
            m, f,
            extra_compile_args=["-O1"]
        )
        for m, f in extensions_dict.items()
    )
    ext_count = len(ext_modules)
    nthreads = ext_count if ext_count < 10 else 10

    if any([a for a in ['-h', '--help'] if a in sys.argv]):
        pass
    elif has_cython and ('compile' in sys.argv or 'bdist_wheel' in sys.argv):
        cy_kwargs = dict(
            nthreads=nthreads,
            force=True,
            language_level=2
        )
        return cythonize(ext_modules, **cy_kwargs), extensions_dict
    return ext_modules, extensions_dict


class _Compile(_sdist):
    extensions_dict = dict()

    def __filter_files(self, files):
        for _files in self.extensions_dict.values():
            for file in _files:
                if file in files:
                    files.remove(file)
        return files

    def make_release_tree(self, base_dir, files):
        if has_cython:
            files = self.__filter_files(files)
        _sdist.make_release_tree(self, base_dir, files)

    def run(self):
        return _sdist.run(self)


class GithubRelease(Command):
    '''
    Make release on github via githubrelease
    '''
    description = 'Make release on github via githubrelease'

    user_options = [
        ('body=', 'b', 'Body message.'),
        ('assets=', 'a', 'Release assets patterns.'),
        ('repo=', 'r', 'Repository for release.'),
        ('release=', 'R', 'Release version.'),
        ('dry-run=', 'd', 'Dry run.'),
        ('publish=', 'p', 'Publish release or just create draft.'),
    ]

    def initialize_options(self):
        self.body = None or os.getenv('CI_COMMIT_DESCRIPTION', None)
        self.assets = None
        self.repo = None
        self.dry_run = False
        self.publish = False
        self.release = None or self.distribution.metadata.version

    def finalize_options(self):
        if self.repo is None:
            raise Exception("Parameter --repo is missing")
        if self.release is None:
            raise Exception("Parameter --release is missing")
        self._gh_args = (self.repo, self.release)
        self._gh_kwargs = dict(
            publish=self.publish, name=self.release, dry_run=self.dry_run
        )
        if self.assets:
            assets = self.assets.format(release=self.release)
            assets = list(filter(bool, assets.split('\n')))
            self._gh_kwargs['asset_pattern'] = assets
        if self.body:
            self._gh_kwargs['body'] = self.body

    def run(self):
        from github_release import gh_release_create
        gh_release_create(*self._gh_args, **self._gh_kwargs)


class build_py(build_py_orig):
    exclude = []
    compile_extentions_types = ['.py', '.pyx']
    wheel_extentions_types = ['.c', '.cpp'] + compile_extentions_types

    def _filter_modules(self, module_tuple):
        pkg, mod, file = module_tuple
        try:
            file_name, file_ext = os.path.splitext(file)
            module_name = file_name.replace('/', '.')
        except:
            return True
        if 'bdist_wheel' in sys.argv:
            exclude_list = self.wheel_extentions_types
        elif 'compile' in sys.argv:
            exclude_list = self.compile_extentions_types
        else:
            return True
        if module_name in self.exclude and file_ext in exclude_list:
            return False
        return True

    def find_package_modules(self, package, package_dir):
        modules = build_py_orig.find_package_modules(self, package, package_dir)
        return list(filter(self._filter_modules, modules))


class install_lib(_install_lib):
    exclude = []

    def _filter_files_with_ext(self, filename):
        _filename, _fext = os.path.splitext(filename)
        if _fext in build_py.wheel_extentions_types:
            return True
        return False

    def install(self):
        result = _install_lib.install(self)
        files = list(listfiles(self.install_dir))
        so_extentions = list(filter(lambda f: fnmatch.fnmatch(f, '*.so'), files))
        for source in filter(self._filter_files_with_ext, files):
            _source_name, _source_ext = os.path.splitext(source)
            if any(filter(lambda f: fnmatch.fnmatch(f, _source_name+"*.so"), so_extentions)):
                print('Removing extention sources [{}].'.format(source))
                os.remove(source)
        return result


def get_compile_command(extensions_dict=None):
    extensions_dict = extensions_dict or dict()
    compile_class = _Compile
    compile_class.extensions_dict = extensions_dict
    return compile_class


def make_setup(**opts):
    if 'packages' not in opts:
        opts['packages'] = find_packages()
    ext_modules_list = opts.pop('ext_modules_list', list())
    ext_mod, ext_mod_dict = make_extensions(ext_modules_list)
    opts['ext_modules'] = opts.get('ext_modules', list()) + ext_mod
    cmdclass = opts.get('cmdclass', dict())
    if 'compile' not in cmdclass:
        cmdclass.update({"compile": get_compile_command(ext_mod_dict)})
    if has_cython:
        build_py.exclude = ext_modules_list
        cmdclass.update({
            'build_ext': _build_ext,
            'build_py': build_py,
            'install_lib': install_lib
        })
    if has_sphinx and 'build_sphinx' not in cmdclass:
        cmdclass['build_sphinx'] = BuildDoc
    cmdclass['githubrelease'] = GithubRelease
    opts['cmdclass'] = cmdclass
    setup(**opts)

########################################################################################
# end block


ext_list = [
    "polemarch.api.v2.filters",
    "polemarch.api.v2.permissions",
    "polemarch.api.v2.serializers",
    "polemarch.api.v2.swagger",
    "polemarch.api.v2.views",
    "polemarch.api.signals",
    "polemarch.main.models.base",
    "polemarch.main.models.hooks",
    "polemarch.main.models.hosts",
    "polemarch.main.models.projects",
    "polemarch.main.models.tasks",
    "polemarch.main.models.users",
    "polemarch.main.models.utils",
    "polemarch.main.models.vars",
    "polemarch.main.templatetags.inventories",
    'polemarch.main.settings',
    'polemarch.main.hooks.base',
    'polemarch.main.hooks.http',
    'polemarch.main.hooks.script',
    'polemarch.main.repo._base',
    'polemarch.main.repo.manual',
    'polemarch.main.repo.tar',
    'polemarch.main.repo.vcs',
    'polemarch.main.validators',
]

if 'develop' in sys.argv:
    ext_list = []

kwargs = dict(
    name='polemarch',
    ext_modules_list=ext_list,
    include_package_data=True,
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*",
    install_requires=[
    ] +
    load_requirements('requirements.txt', os.getcwd()) +
    load_requirements('requirements-doc.txt', os.getcwd()),
    extras_require={
        'test': load_requirements('requirements-test.txt', os.getcwd()),
    },
    dependency_links=[
    ] + load_requirements('requirements-git.txt', os.getcwd()),
    project_urls={
        "Issue Tracker": "https://gitlab.com/vstconsulting/polemarch/issues",
        "Documentation": "http://polemarch.readthedocs.io/",
        "Source Code": "https://gitlab.com/vstconsulting/polemarch",
        "Releases": "https://github.com/vstconsulting/polemarch/releases",
        "Docker": "https://hub.docker.com/r/vstconsulting/polemarch/",
    },
    entry_points={
        'console_scripts': ['polemarchctl=polemarch:cmd_execution']
    },
)

if __name__ == '__main__':
    make_setup(**kwargs)
