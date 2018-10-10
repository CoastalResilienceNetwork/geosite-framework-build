import argparse
import errno
import json
import os
import posixpath
import shutil
import stat
import sys
import distutils

from distutils.dir_util import copy_tree
from subprocess import call


FRAMEWORK_REPO = 'GeositeFramework'
DEFAULT_ORG = 'CoastalResilienceNetwork'
DEFAULT_BRANCH = 'master'
BUILD_DIR = 'build'     # Build workspace
OUTPUT_DIR = 'output'   # Installer artifact directory


def build_region(region, path, full_framework, framework_branch=None,
                 region_branch=None, is_prod=False):
    """ Build a GeositeFramework Region Installer and optionally install it """
    workspace = setup_workspace(path)

    # Get the repo name and to avoid confusion name it a _config dir
    region_dest = '%s_config' % region.split('/')[1]
    region_name = get_region_name(region)

    # If installing to dev site, favor a branch named 'development' for the
    # region repo and any plugins, but don't fail if it doesn't exist
    # This is the convention used by TNC developers to introduce new features
    if region_branch:
        # An override was provided, use it
        region_branch = region_branch
    elif is_prod:
        # Production build, use master (default)
        region_branch = None
    else:
        # Dev site, with no region-branch override
        region_branch = 'development'

    clone_repo(region, region_dest, branch=region_branch)

    fetch_framework_and_plugins(region_dest, framework_branch, region_branch)
    copy_region_files(workspace, region_dest)
    build_project(workspace)
    zip_project(workspace, region_name)

    print ""
    print "---------------------------------------"
    print "%s was built successfully" % region
    print "---------------------------------------"
    print ""


def get_region_name(repo_name):
    # Strip off the org/ from the repo
    repo = repo_name[repo_name.find('/')+1:]

    # convention is to take region repo, minus text "-region",
    # thus gulfmex-region become url "gulfmex"
    region = repo[0:repo.find('-region')]

    return region


def build_from_config(config, workspace_dir, full_framework, is_prod):
    """Build each region in the specified config file"""
    if not os.path.isfile(config):
        print '%s cannot be found in %s' % (config, workspace_dir)
        sys.exit(1)

    with open(config) as config_file:
        regions = config_file.readlines()
        for region in regions:
            build_region(region.rstrip(), workspace_dir, full_framework,
                         DEFAULT_BRANCH, DEFAULT_BRANCH, is_prod)


def fetch_framework_and_plugins(region_dest, framework_branch=None,
                                region_branch=None):
    """ Read in the region's plugin config and clone the specified repos """

    os.chdir(region_dest)
    if not os.path.isfile('plugins.json'):
        print '%s does not specifiy a plugins.json, not fetching plugins.' \
            % (region_dest)
        os.chdir('..')
        clone_repo(full_framework, branch=framework_branch)
    else:
        with open('plugins.json') as plugins:
            config = json.load(plugins)
            os.chdir('..')

            framework_ver = config.get('frameworkVersion')
            clone_repo(full_framework, branch=framework_branch,
                       version=framework_ver)

            fetch_plugins(config['plugins'], region_branch)


def fetch_plugins(plugins, branch=None):
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

        clone_repo(full_repo, target_dir, version, branch)


def remove_git_dir(target_dir):
    """ Remove git files from installed framework components """
    parent_dir = os.getcwd()
    git_dir = os.path.join(parent_dir, target_dir, '.git')
    shutil.rmtree(git_dir, ignore_errors=False,
                  onerror=handle_remove_readonly)


def copy_region_files(workspace, region_dest):
    """ Move region specific files into the framework base """
    src_dir = os.path.join(workspace, FRAMEWORK_REPO,
                           'src', 'GeositeFramework')
    os.chdir(os.path.join(workspace, region_dest))

    files = ['region.json', 'partners.html', 'Proxy.config']
    copy_files(files, src_dir)

    directories = ['plugins', 'img', 'Views', 'methods', 'sims', 'xml', 'docs',
                   'locales']
    copy_dirs(directories, src_dir)


def copy_files(files, src_dir):
    for f in files:
        print 'Copying %s...' % f
        overwrite_copy(f, src_dir, True)


def copy_dirs(directories, src_dir):
    for directory in directories:
        print 'Copying %s...' % directory
        overwrite_copy(directory, os.path.join(src_dir, directory))


def handle_remove_readonly(func, path, exc):
    """ If shutil.rmtree failed for a readonly file, change the permissions and
        try again
    """
    excvalue = exc[1]
    if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCES:
        os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 0777
        func(path)
    else:
        raise


def overwrite_copy(file_or_dir, dest, single_file=False):
    """ Copy files or folders to the specified destination """
    try:
        if single_file:
            shutil.copy(file_or_dir, dest)
        else:
            copy_tree(file_or_dir, dest)
    except (IOError, OSError, distutils.errors.DistutilsFileError) as e:
        print(e)


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


def clone_repo(full_repo, target_dir=None, version=None, branch=None):
    """ Clone a public repo via https.  Specify `version` to target a
        specific commit sha
    """
    original_dir = os.getcwd()

    # Get the actual name that git will clone to
    dest = (target_dir or os.path.split(full_repo)[1])
    print 'Cloning %s@%s...' % (dest, (version or "HEAD"))

    repo_url = posixpath.join('https://github.com/' '%s.git' % full_repo)
    clone_args = ['git', 'clone', '--quiet', repo_url]

    # Reduce the amount of git history that is cloned if the history is not
    # needed.
    if version is None:
        clone_args.extend(['--depth', '1', '--no-single-branch'])

    if target_dir:
        clone_args.append(target_dir)

    execute(clone_args)

    if branch:
        # Attempt to check out a remote branch, but don't fail if it doesn't
        # exist. This is typically used to attempt a 'development' branch,
        # which is a convention used by TNC plugin/region developers for
        # pre-production code.
        os.chdir(dest)

        execute(['git', 'fetch', 'origin'])

        # Don't print any errors for checking out branch, there's no good way
        # to check if a remote branch exists programmatically. And if it
        # doesn't, git stays on the current branch.
        print 'Attempting to checkout the %s branch' % branch
        execute(['git', 'checkout', branch, '2>', 'nul'], [1])
        os.chdir(original_dir)

    if version:
        os.chdir(dest)
        execute(['git', 'reset', '--hard', version])
        os.chdir(original_dir)

    # Clean-up. Git specific files are not needed for the installation
    remove_git_dir(dest)


def build_project(root):
    """ Run framework Python scripts to build static site. """
    framework_dir = os.path.join(root, 'GeositeFramework')
    os.chdir(framework_dir)

    # Run build script
    execute(['python', 'scripts/main.py'])


def zip_project(root, region_name):
    """ Zip up the built source files """
    src_dir = os.path.join(root, 'GeositeFramework', 'src')
    parent_dir = os.path.join('..', '..')
    shutil.make_archive(os.path.join(parent_dir, 'output',
                        region_name), 'zip', src_dir)


def execute(call_args, additional_success_codes=[]):
    """ Check the exit code for a subprocess call for errors.
        By default, 0 is ok, but the caller can provide
        additional_success_codes that should be considered non-errors
    """

    exit = call(" ".join(call_args), shell=True)
    if exit != 0 and exit not in additional_success_codes:
        print "Call to %s failed" % call_args
        sys.exit()


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
    parser.add_argument('--region-branch', default=DEFAULT_BRANCH,
                        nargs='?', help='Region repo branch to use. ' +
                        'Overridden by --dev and --prod options. ' +
                        'Default=%s' % DEFAULT_BRANCH)
    parser.add_argument('--framework-branch', default=DEFAULT_BRANCH,
                        nargs='?', help='Framework repo branch to use. ' +
                        'Default=%s' % DEFAULT_BRANCH)
    parser.add_argument('--config', default=False, action='store_true',
                        help='Source input was a configuration file for ' +
                             'building multiple regions at once')
    parser.add_argument('--prod', default=False, action='store_true',
                        help='Use the master branch for the region')

    args = parser.parse_args()

    is_prod = args.prod
    framework_branch = (args.framework_branch if args.framework_branch
                        else DEFAULT_BRANCH)
    region_branch = (args.region_branch if args.region_branch
                     else DEFAULT_BRANCH)

    full_framework = posixpath.join(DEFAULT_ORG, FRAMEWORK_REPO)
    cwd = os.getcwd()

    if args.config:
        build_from_config(args.source, cwd, full_framework, is_prod)
    else:
        region = posixpath.join(args.org, args.source)
        build_region(region, cwd, full_framework, framework_branch,
                     region_branch, is_prod)
