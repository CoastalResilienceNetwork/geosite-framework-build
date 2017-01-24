import argparse
import errno
import json
import os
import posixpath
import shutil
import stat
import sys

from subprocess import call

# ******************************
# May need to change these for non-TNC installations
# IIS Website names for production and development deployments
PROD_SITE = 'Default Web Site'
DEV_SITE = 'dev'

# Root paths for production and development installations
PROD_PATH = 'C:\\projects\\TNC'
DEV_PATH = 'C:\\projects\\TNC\\dev'

# Default installer name
INSTALLER_NAME = 'output\\tnc-ca-%(region)s%(env)sSetup.exe'

# ******************************

# Default path for SDK installs of MSBuild
MSBUILD_PATH = 'C:\\Windows\Microsoft.NET\\Framework\\v4.0.30319\\MSBuild.exe'
# Assume that NSIS install path is on the path
NSIS_EXE = 'makensis.exe'

FRAMEWORK_REPO = 'GeositeFramework'
DEFAULT_ORG = 'CoastalResilienceNetwork'
DEFAULT_BRANCH = 'master'
BUILD_DIR = 'build'     # Build workspace
OUTPUT_DIR = 'output'   # Installer artifact directory
# NSIS Compiler Verbosity Setting 0 (off) - 4 (all)
NSIS_V = 0
# MSBUILD Compiler Verbosity q[uiet], m[inimal], n[ormal], d[etailed]
MSB_V = 'q'


def build_region(region, path, full_framework, framework_branch=None,
                 region_branch=None, do_install=False, is_prod=False,
                 is_test=False):
    """ Build a GeositeFramework Region Installer and optionally install it """
    workspace = setup_workspace(path)

    # Get the repo name and to avoid confusion name it a _config dir
    region_dest = '%s_config' % region.split('/')[1]
    region_name = get_region_name(region)

    # If installing to dev site, favor a branch named 'development' for the
    # region repo and any plugins, but don't fail if it doesn't exist
    # This is the convention used by TNC developers to introduce new features
    region_branch = ('development' if do_install and not is_prod else
                     region_branch)

    clone_repo(region, region_dest, branch=region_branch)

    fetch_framework_and_plugins(region_dest, framework_branch, region_branch)
    copy_region_files(workspace, region_dest)
    compile_project(workspace)

    if (is_test):
        region_name = "test"

    make_installer(workspace, region_dest, region_name, is_prod)

    if do_install:
        install(region_name, path, is_prod)

    print ""
    print "---------------------------------------"
    print "%s was build successfully" % region
    print "---------------------------------------"
    print ""


def get_region_name(repo_name):
    # Strip off the org/ from the repo
    repo = repo_name[repo_name.find('/')+1:]

    # convention is to take region repo, minus text "-region",
    # thus gulfmex-region become url "gulfmex"
    region = repo[0:repo.find('-region')]

    return region


def install(region, path, is_prod=False):
    """Run the installer in silent mode to install to prod or dev website"""

    print "Installing to %s" % ("production" if is_prod else "development")

    exe_name = INSTALLER_NAME % {'region': region, 'env': '' if is_prod
                                 else '-dev'}
    url = region
    website = PROD_SITE if is_prod else DEV_SITE
    root_path = PROD_PATH if is_prod else DEV_PATH
    install_path = os.path.join(root_path, region)

    args = [exe_name,
            '/S',
            '/WEBSITE_NAME=%s' % website,
            '/APP_URL=%s' % url,
            '/REINSTALL_OVER=true',
            '/D=%s' % install_path]

    os.chdir(path)
    execute(args)


def build_from_config(config, workspace_dir, full_framework, do_install,
                      is_prod):
    """Build each region in the specified config file"""
    if not os.path.isfile(config):
        print '%s cannot be found in %s' % (config, workspace_dir)
        sys.exit(1)

    with open(config) as config_file:
        regions = config_file.readlines()
        for region in regions:
            build_region(region.rstrip(), workspace_dir, full_framework,
                         DEFAULT_BRANCH, DEFAULT_BRANCH,
                         do_install, is_prod)


def make_installer(workspace_dir, region_dest, region_name, is_prod=False):
    os.chdir(workspace_dir)
    install_scripts_dir = 'installer'
    full_region_nsi_path = os.path.join(workspace_dir,
                                        install_scripts_dir, 'installer.nsi')
    template_nsi = os.path.join(install_scripts_dir, 'installer.nsi.tmpl')

    print "Creating installer executable..."

    # Get all of the NSIS installers scripts together in a single directory
    os.mkdir(install_scripts_dir)
    clone_repo('azavea/azavea-nsis', os.path.join(install_scripts_dir, 'NSIS'))
    overwrite_copy('..\installer-scripts\*', install_scripts_dir)

    # Load installer template
    with open(template_nsi, 'r') as installer:
        tmpl = installer.read()
        installer_name = region_name + ('' if is_prod else '-dev')
        installer_contents = tmpl % {'region': installer_name}

        # Copy the region specific installer to the region_dest
        with open(full_region_nsi_path, 'w') as output_nsi:
            output_nsi.write(installer_contents)

    # Compile an executable installer for this region
    verbosity = '/V%s' % NSIS_V
    execute([NSIS_EXE, verbosity, full_region_nsi_path])

    # Copy the exe to the output dir
    root_dir, _ = os.path.split(workspace_dir)
    dest = os.path.join(root_dir, OUTPUT_DIR)
    src = os.path.join(workspace_dir, install_scripts_dir, '*.exe')
    overwrite_copy(src, dest)


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
    args = ['rmdir', '/s', '/q', ('%s\\%s\\.git') % (parent_dir, target_dir)]
    execute(args)


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
        os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 0777
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

    # Exit code 0 (success) and 4 (No files to copy) should succeed
    execute(copy_args, [4])


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


def compile_project(root):
    """ Compile the .NET project with MSBuild """
    os.chdir(root)

    # Consent to Nuget Package Restore by default
    os.environ['EnableNuGetPackageRestore'] = 'True'

    verbosity = '/verbosity:%s' % MSB_V
    execute([MSBUILD_PATH, verbosity, '/p:Configuration=Release',
            'GeositeFramework\src\GeositeFramework.sln'])


def execute(call_args, additional_success_codes=[]):
    """ Check the exit code for a subprocess call for errors.
        By default, 0 is ok, but the caller can provide
        additional_success_codes that should be considered non-errors
    """

    exit = call(call_args, shell=True)
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
    parser.add_argument('--dev', default=False, action='store_true',
                        help='Install this region to the development ' +
                             'environment')
    parser.add_argument('--prod', default=False, action='store_true',
                        help='Install this region to the production ' +
                             'environment')
    parser.add_argument('--silent', default=False, action='store_true',
                        help='Install this region without the prompt, ' +
                             'mostly for scripts')
    parser.add_argument('--test', default=False, action='store_true',
                        help='Install this region to the test site. ' +
                             'Only valid if dev or prod is also selected')

    args = parser.parse_args()

    # Check if we are auto installing this build
    if args.prod and args.dev:
        print "Please choose only 'prod' or 'dev'"
        sys.exit()

    do_install = args.prod or args.dev
    is_prod = args.prod
    is_test = args.test
    framework_branch = (args.framework_branch if args.framework_branch
                        else DEFAULT_BRANCH)
    region_branch = (args.region_branch if args.region_branch
                     else DEFAULT_BRANCH)

    if do_install:
        if not args.silent:
            choice = raw_input('This will remove any current installation ' +
                               'and install a new region website. Are you ' +
                               'sure you wish to continue? [y/n]: ')
            if choice.lower() not in ['y', 'yes']:
                sys.exit()

    full_framework = posixpath.join(DEFAULT_ORG, FRAMEWORK_REPO)
    cwd = os.getcwd()

    if args.config:
        build_from_config(args.source, cwd, full_framework, do_install,
                          is_prod)
    else:
        region = posixpath.join(args.org, args.source)
        build_region(region, cwd, full_framework, framework_branch,
                     region_branch, do_install, is_prod, is_test)
