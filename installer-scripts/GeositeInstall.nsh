!INCLUDE "WebApp.nsh"

;------------------------------------------------------------------------------
; Install a region-specific version of the Geosite Framework
;
; NAME      - For naming files and URLs (should not contain spaces)
; NICE_NAME - For display and titles
;
!MACRO MakeGeositeInstaller NAME NICE_NAME

;;; Generate installer part 1 -- NICE_NAME MAJOR_VER MINOR_VER DEFAULT_INST_DIR APP_URL WEBSITE_NAME APP_POOL_NAME

!INSERTMACRO BeginApp "${NICE_NAME}" "1" "0" "C:\projects\TNC\${NAME}" "${NAME}" "Default Web Site" "DefaultAppPool"

;;; Files unique to this application

Section "Web Files"
    SetOutPath $APPLICATION_DIR
    File ..\GeositeFramework\src\GeositeFramework\Global.asax
    File ..\GeositeFramework\src\GeositeFramework\Web.config

    SetOutPath $APPLICATION_DIR\bin
    File ..\GeositeFramework\src\GeositeFramework\bin\*.dll

    SetOutPath $APPLICATION_DIR
    File /r  ..\GeositeFramework\src\GeositeFramework\App_Data
    File /r  ..\GeositeFramework\src\GeositeFramework\Error.html
    File /r  ..\GeositeFramework\src\GeositeFramework\Error404.html
    File /r  ..\GeositeFramework\src\GeositeFramework\Global.asax
    File /r  ..\GeositeFramework\src\GeositeFramework\Web.config
    File /r  ..\GeositeFramework\src\GeositeFramework\css
    File /r  ..\GeositeFramework\src\GeositeFramework\img
    File /r  ..\GeositeFramework\src\GeositeFramework\js
    File /nonfatal /r  ..\GeositeFramework\src\GeositeFramework\fonts
    File /r  ..\GeositeFramework\src\GeositeFramework\plugins
    File /r  ..\GeositeFramework\src\GeositeFramework\sample_plugins
    File /r  ..\GeositeFramework\src\GeositeFramework\proxy.ashx
    File /r  ..\GeositeFramework\src\GeositeFramework\proxy.config
    File /r  ..\GeositeFramework\src\GeositeFramework\region.json
    File /nonfatal ..\GeositeFramework\src\GeositeFramework\partners.html
    File /r  ..\GeositeFramework\src\GeositeFramework\Scripts

    ; Common but optional additional directories to copy
    File /nonfatal /r ..\GeositeFramework\src\GeositeFramework\locales
    File /nonfatal /r ..\GeositeFramework\src\GeositeFramework\xml
    File /nonfatal /r ..\GeositeFramework\src\GeositeFramework\sims
    File /nonfatal /r ..\GeositeFramework\src\GeositeFramework\methods
    File /nonfatal /r ..\GeositeFramework\src\GeositeFramework\docs

    SetOutPath $APPLICATION_DIR\Views
    File /r ..\GeositeFramework\src\GeositeFramework\Views\*.cshtml
    File ..\GeositeFramework\src\GeositeFramework\Views\Web.config   ;Internal Web.config for ASP.NET MVC Views
SectionEnd

;;; Generate installer part 2 -- DISPLAY_NAME DEFAULT_DOC DOTNETVER

!INSERTMACRO FinishSite "${NICE_NAME}" "Global.asax" "4"

!MACROEND
