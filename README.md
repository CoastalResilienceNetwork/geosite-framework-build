geosite-framework-build
=======================

Build script for GeositeFramework regions

### Usage Instructions
#### For a single region
To run the script at a command prompt, run the following command:

``python build.py [region_repo_name] [optional: github_organization]``

where:
  * ``region_repo_name``: The name of the GeositeFramework Region Repo on  Github.com
  * ``github_organization``: Optional.  The name of the Github.com Organization which the repo belongs to. Default is CoastalResilienceNetwork.

For example, to build the Gulf of Mexico region site, the command would look like this:

``python build.py gulf-of-mexico-region``

That will assemble and build the gulfmex Coastal Resilience site in a workspace in the current directory.

To build a region in another github organization, an example could be:
``python build.py TNC-LA-Freshwater azavea``

which will build the ``azavea/TNC-LA-Freshwater`` region, assuming the region has been updated to conform to the build script requirements (See: Setting up a Region Repo)

The executable installer will be in the ``[workspace]\output`` folder after the script runs successfully.

#### Using the build script to set up a development environment
The same script leaves all of the intermediate code in the ``[workspace]\build`` directory so that plugin developers need only to create an IIS Application which points to ``[workspace]\build\GeositeFramework\src\GeositeFramework``.  This will be a working version of the region and all of its plugins, ready to be served.

#### Building multiple regions at once
The build script can build installers for multiple sites at once by use of a config file and a flag to the script.  If you created a Coastal Resilience file named ``ca.conf`` with the contents being one full Org/Repo per line:

```
CoastalResilienceNetwork/gulf-of-mexico-region
CoastalResilienceNetwork/ventura-region
CoastalResilienceNetwork/puget-sound-region
```

You can then run the build script with the following:

``python build.py ca.conf --config``

and it will build all regions listed in the conf file.  The output of all installers will still be in ``[workspace]\output``.  Note that the build process does *not* clear out the output directory, so you may also have old installers there.  The script *will* overwrite any files in ``output`` with newer versions.

#### Errors and debugging the script
##### Error deleteing ``build`` directory
Occasionally, you may get an error that the ``build`` directory can not be deleted.  This can happen when IIS has a lock on a file coupled with a limitation with the python ``shutil.rmtree`` method on Windows.  Simply re-running the script will fix the issue.

##### Errors with the .NET compiler or NSIS Compiler
Both compilers are set to ``quiet`` mode so their output is supressed.  The top of the build script exposes settings to increase the verbosity of the compiler output.

### Setting up a Region Repo
To see a complete example Region Repo, see [Gulf of Mexico](https://github.com/CoastalResilienceNetwork/gulf-of-mexico-region).
The build script makes certain assumptions about the structure and content of a Region Repo to be able to work generically across multiple regions.  The basic structure of the [region.json](https://github.com/CoastalResilienceNetwork/GeositeFramework/wiki/Region.json-Settings) file is unchanged.  A region repo should contain the following files:
  * ``region.json``: Main configuration file for a region site
  * ``proxy.config``: Proxy information for what URLs a region site can proxy HTTP requests for.
  * ``partners.html``: Optional.  Custom HTML for a "partners" popup.
  * ``installer.nsi``: An NSIS Compiler script.
  * ``plugins.json``: A json config that specifies which remote plugins are need to be fetched for this region at build time.
  * ``plugins`` directory: A directory of named plugin directories that contain the specific configuration for a plugin, but not the plugin code itself.

#### installer.nsi contents
To allow the build script to compile an executable installer for the region, you must include an ``installer.nsi`` file.  The contents of the file should be similar to:

```
!DEFINE APP_NAME "TNC_CR_GulfOfMexico"

!INCLUDE "GeositeInstall.nsh"

!INSERTMACRO MakeGeositeInstaller "gulfmex" "TNC Coastal Resilience: Gulf of Mexico"

```
The ``APP_NAME`` will be the filename of the installer, as well as the key which the installer will use to determine if that region is already installed on a system, and offer to uninstall if so.

The ``MakeGeositeInstaller`` macro line takes two arguments, the IIS URL that the app should be served from ("gulfmex" in this example) and the "Pretty Name" that will be presented on the installer dialog.

You should only need to modify those three arguments to repurpose the install script for a new region.


#### plugins.json contents
plugins.json should be a valid json document.  You can use an online tool such as [http://jsonlint.com/](http://jsonlint.com/) to validate your json.  The file contains the specifications of which plugins to include in the region.

```json
{
  "frameworkVersion": "d84546bb",

  "plugins": [
    {
      "repo": "explorer",
      "name": "habitat_explorer",
      "ver": "2bd47452"
    },
    {
      "repo": "explorer",
      "name": "risk_explorer"
    },
    {
      "repo": "3dparty_plugin",
      "name": "Test Plugin",
      "org": "OtherOrg"
    }
  ]
}
```
  * ``frameworkVersion``:  If the region wants to target an older framework git commit enter the sha, if not supplied it will pull hte most recent version. 
  * ``repo``: github.com repository name.
  * ``name``: The plugin directory to copy the code into in the region site.  It should be the directory that the region plugin config will be in.
  * ``ver``: Optional.  The git commit to target in the plugin repo, if not supplied it will pull the most recent version. 
  * ``org``: Optional.  The github org this repo belongs to.  Default is CoastalResilienceNetwork.

### Setting up a Plugin Repo
A plugin repo should contain all of the source code for a single plugin, specifically the ``main.js`` file and any other supporting files.  For examples, see:

  * [multiSelect](https://github.com/CoastalResilienceNetwork/multiSelect)
  * [feature-compare](https://github.com/CoastalResilienceNetwork/feature-compare)
  * [explorer](https://github.com/CoastalResilienceNetwork/explorer)

### Installation Instructions
The build machine will need the following dependencies:

  * ``python 2.7+``: This is often included in ESRI installations, but should be accessible from the ``PATH``.
  * ``MSBuild.exe``: This should be available if the .NET SDK v4 has been installed
  * ``NSIS``: Installer script system. Download at http://nsis.sourceforge.net/Main_Page. Must be available on the ``PATH``.
  * ``git``: The git source control command must be available on the ``PATH``. http://git-scm.com/downloads
