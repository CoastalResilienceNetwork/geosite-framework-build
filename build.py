import argparse
import errno
import json
import os
import posixpath
import shutil
import stat
import sys

from subprocess import call

# Default path for SDK installs of MSBuild
MSBUILD_PATH = 'C:\\Windows\Microsoft.NET\\Framework\\v4.0.30319\\MSBuild.exe'
# Assume that NSIS install path is on the path
NSIS_EXE = 'makensis.exe'

FRAMEWORK_REPO = 'GeositeFramework'
DEFAULT_ORG = 'CoastalResilienceNetwork'
BUILD_DIR = 'build'     # Build workspace
OUTPUT_DIR = 'output'   # Installer artifact directory
# NSIS Compiler Verbosity Setting 0 (off) - 4 (all)
NSIS_V = 0
# MSBUILD Compiler Verbosity q[uiet], m[inimal], n[ormal], d[etailed]
MSB_V = 'q'


def build_region(region, path, full_framework):
    """ Build a GeositeFramework Region Installer """
    workspace = setup_workspace(path)

    # Get the repo name and to avoid confusion name it a _config dir
    region_dest = '%s_config' % region.split('/')[1]

    clone_repo(region, region_dest)

    fetch_framework_and_plugins(region_dest)
    copy_region_files(workspace, region_dest)
    compile_project(workspace)
    make_installer(workspace, region_dest)

    print ""
    print "---------------------------------------"
    print "%s was build successfully" % region
    print "---------------------------------------"
    print ""


def build_from_config(config, workspace_dir, full_framework):
    """Build each region in the specified config file"""
    if not os.path.isfile(config):
        print '%s cannot be found in %s' % (config, workspace_dir)
        sys.exit(1)
        
    with open(config) as config_file:
        regions = config_file.readlines()
        for region in regions:
            build_region(region.rstrip(), workspace_dir, full_framework)


def make_installer(workspace_dir, region_dest):
    os.chdir(workspace_dir)
    install_scripts_dir = 'installer'
    region_install_file = 'installer.nsi'

    print "Creating installer executable..."

    # Get all of the NSIS installers scripts together in a single directory
    os.mkdir(install_scripts_dir)
    clone_repo('azavea/azavea-nsis', os.path.join(install_scripts_dir, 'NSIS'))
    overwrite_copy('..\installer-scripts\*', install_scripts_dir)
    region_installer = os.path.join(os.getcwd(), region_dest,
                                    region_install_file)
    overwrite_copy(region_installer, install_scripts_dir)

    # Compile an executable installer for this region
    installer_path = os.path.join(workspace_dir, install_scripts_dir,
                                  region_install_file)
    verbosity = '/V%s' % NSIS_V
    execute([NSIS_EXE, verbosity, installer_path])

    # Copy the exe to the output dir
    root_dir, _ = os.path.split(workspace_dir)
    dest = os.path.join(root_dir, OUTPUT_DIR)
    src = os.path.join(workspace_dir, install_scripts_dir, '*.exe')
    overwrite_copy(src, dest)


def fetch_framework_and_plugins(region_dest):
    """ Read in the region's plugin config and clone the specified repos """

    os.chdir(region_dest)
    if not os.path.isfile('plugins.json'):
        print '%s does not specifiy a plugins.json, not fetching plugins.' \
               % (region_dest)
        os.chdir('..')
        clone_repo(full_framework)
    else:
        with open('plugins.json') as plugins:
            config = json.load(plugins)
            os.chdir('..')

            framework_ver = config.get('frameworkVersion')
            clone_repo(full_framework, version=framework_ver)

            fetch_plugins(config['plugins'])


def fetch_plugins(plugins):
    """ Clone each specified plugin at its optional version """

    plugin_dir = os.path.join(FRAMEWORK_REPO, 'src',
                              'GeositeFramework', 'plugins')

    for plugin in plugins:
        # If org wasn't provided, assume CoastalResilienceNetwork
        org = plugin.get('org', 'CoastalResilienceNetwork')

        # Optionally target a specific commit sha
        version = plugin.get('ver')

        target_dir = os.path.join(plugin_dir, plugin['name'])
        full_repo = posixpath.join(org, plugin['repo'])

        clone_repo(full_repo, target_dir, version)


def copy_region_files(workspace, region_dest):
    """ Move region specific files into the framework base """
    src_dir = os.path.join(workspace, FRAMEWORK_REPO,
                           'src', 'GeositeFramework')
    os.chdir(os.path.join(workspace, region_dest))

    files = ['region.json', 'partners.html', 'Proxy.config']
    copy_files(files, src_dir)

    directories = ['plugins', 'img', 'Views', 'methods', 'sims', 'xml']
    copy_dirs(directories, src_dir)


def copy_files(files, src_dir):
    for file in files:
        print 'Copying %s...' % file
        overwrite_copy(file, src_dir)


def copy_dirs(directories, src_dir):
    for directory in directories:
        print 'Copying %s...' % directory
        overwrite_copy(directory, os.path.join(src_dir, directory), True, True)


def handle_remove_readonly(func, path, exc):
    """ If shutil.rmtree failed for a readonly file, change the permissions and
        try again
    """
    excvalue = exc[1]
    if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCES:
        os.chmod(path, stat.S_IRWXU | stat.S_IRWXG
                 | stat.S_IRWXO)  # 0777
        func(path)
    else:
        raise


def overwrite_copy(file, dest, recursive=False, assume_dir=False):
    """ Perform an XCOPY with optional recursion for child directories """
    copy_args = ['xcopy', file, dest, '/Y', '/Q']
    if recursive:
        copy_args.append('/S')

    if assume_dir:
        copy_args.append('/I')

    call(copy_args, shell=True)


def setup_workspace(path):
    """Move to the specified workspace and create a clean 'build' dir"""
    os.chdir(path)

    # Ensure an output directory exists
    if not os.path.exists(OUTPUT_DIR):
        os.mkdir(OUTPUT_DIR)

    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR, ignore_errors=False,
                      onerror=handle_remove_readonly)

    os.mkdir(BUILD_DIR)
    os.chdir(BUILD_DIR)

    return os.getcwd()


def clone_repo(full_repo, target_dir=None, version=None):
    """ Clone a public repo via https.  Specify `version` to target a
        specific commit sha
    """
    # Get the actual name that git will clone to
    dest = (target_dir or os.path.split(full_repo)[1])
    print 'Cloning %s@%s...' % (dest, (version or "HEAD"))

    repo_url = posixpath.join('https://github.com/' '%s.git' % full_repo)
    clone_args = ['git', 'clone', '--quiet', repo_url]
    if target_dir:
        clone_args.append(target_dir)

    call(clone_args, shell=True)

    if version:
        os.chdir(dest)
        call(['git', 'reset', '--hard', version])
        os.chdir('..')


def compile_project(root):
    """ Compile the .NET project with MSBuild """
    os.chdir(root)
    verbosity = '/verbosity:%s' % MSB_V
    call([MSBUILD_PATH, verbosity, '/p:Configuration=Release',
         'GeositeFramework\src\GeositeFramework.sln'], shell=True)


if (__name__ == '__main__'):
    description = """
        Build a GeositeFramework region instance
    """

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('source', help='Github.com repo of region to build ' +
                        'path to config file for multiple regions')
    parser.add_argument('org', default=DEFAULT_ORG, nargs='?',
                        help='Github.com Org where the repo region resides. ' +
                        'Default=%s' % DEFAULT_ORG)
    parser.add_argument('--config', default=False, action='store_true',
                        help='Source input was a configuration file for building multiple regions at once')

    args = parser.parse_args()

    full_framework = posixpath.join(DEFAULT_ORG, FRAMEWORK_REPO)
    cwd = os.getcwd()

    if args.config:
        build_from_config(args.source, cwd, full_framework)
    else: 
        region = posixpath.join(args.org, args.source)
        build_region(region, cwd, full_framework)
