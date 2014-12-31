;c-style prevention of duplicate imports.
!IFNDEF WEB_APP_IMPORT
!DEFINE WEB_APP_IMPORT "yup"

!ADDINCLUDEDIR "NSIS"
!INCLUDE "SimpleInstallers.nsh"
!INCLUDE "WebAppUtils.nsh"

; Macros to install a web app, without fancy config merging.

;------------------------------------------------------------------------------
; This is the top half of installing a web app or web site
;
!MACRO BeginApp NICE_NAME MAJOR_VER MINOR_VER DEFAULT_INST_DIR APP_URL WEBSITE_NAME APP_POOL_NAME
  !INSERTMACRO BeginApp_1 "${NICE_NAME}" "${MAJOR_VER}" "${MINOR_VER}" "${DEFAULT_INST_DIR}" "${APP_URL}"

  ; Ask the user for the website name.
  !INSERTMACRO WebsiteNamePage
  ; Ask the user for the application pool name.
  !INSERTMACRO AppPoolNamePage

  !INSERTMACRO BeginApp_2 "${WEBSITE_NAME}" "${APP_POOL_NAME}"
!MACROEND

!MACRO BeginSite NICE_NAME MAJOR_VER MINOR_VER DEFAULT_INST_DIR APP_URL
  !INSERTMACRO BeginApp_1 "${NICE_NAME}" "${MAJOR_VER}" "${MINOR_VER}" "${DEFAULT_INST_DIR}" "${APP_URL}"
  Var "WEBSITE_NAME"  ;Unused but must declare for other macros
  Var "APP_POOL_NAME" ;Unused but must declare for other macros
  !INSERTMACRO BeginApp_2 "Default Web Site" ""
!MACROEND

;------------------------------------------------------------------------------
; Components of the top half of installing a web app
;
!MACRO BeginApp_1 NICE_NAME MAJOR_VER MINOR_VER DEFAULT_INST_DIR APP_URL
  Name "${NICE_NAME}"
  OutFile "${APP_NAME}Setup.exe"
  InstallDir "${DEFAULT_INST_DIR}"

  !DEFINE APP_MAJOR_VERSION "${MAJOR_VER}"
  !DEFINE APP_MINOR_VERSION "${MINOR_VER}"

  !INCLUDE "AzaveaUtils.nsh"
  !INCLUDE "ConfigUtils.nsh"
  !INCLUDE "StandardQuestions.nsh"
  !INCLUDE "MUI.nsh"

  !INSERTMACRO MUI_PAGE_WELCOME
  ; Ask the user to choose an install directory.
  !INSERTMACRO MUI_PAGE_DIRECTORY

  ; Ask the user for the virtual directories.
  !INSERTMACRO AvStandardVirtualDirectoryPage
!MACROEND

!MACRO BeginApp_2 WEBSITE_NAME APP_POOL_NAME
  ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
  ;;; Extracted from 'SimpleInstall' macros

  ; Page to show while installing the files.
  !INSERTMACRO MUI_PAGE_INSTFILES

  ; On uninstall, show the progress.
  !INSERTMACRO MUI_UNPAGE_CONFIRM
  !INSERTMACRO MUI_UNPAGE_INSTFILES

  ; Tell MUI the language.
  !INSERTMACRO MUI_LANGUAGE "English"

  ; Declare the standard variables (APPLICATION_DIR, CONFIG_DIR, LOG_DIR, TEMPLATES_DIR)
  !INSERTMACRO AvStandardSubdirVariables

  Function .onInit
      Call StartupChecks
      !INSERTMACRO AvStandardQuestionsOnInit
      !INSERTMACRO InitVar APP_URL "${APP_URL}"
      !INSERTMACRO InitVar WEBSITE_NAME "${WEBSITE_NAME}"
      !INSERTMACRO InitVar APP_POOL_NAME "${APP_POOL_NAME}"
  FunctionEnd

  Function .onVerifyInstDir
    !INSERTMACRO AvStandardQuestionsOnVerify
  FunctionEnd

  Section "Install Basics"
    !INSERTMACRO SaveStandardUninstallInfo "azavea_icon_lg.ico" "NSIS"
  SectionEnd

  ;;; End of extract from 'SimpleInstall' macros
  ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

  !INSERTMACRO StandardLogFileSection $LOG_DIR
!MACROEND

;------------------------------------------------------------------------------
; This is the bottom half of installing a web app, a simplified RestOfWebProj
; 
; DISPLAY_NAME    - The display name of the virtual directory, visible in IIS administrator(?)
; DEFAULT_DOC     - The default document, such as "default.asmx".
;
!MACRO FinishSite DISPLAY_NAME DEFAULT_DOC DOTNETVER
  Section "FinishSite"
    !INSERTMACRO RestOfWebProj "$APPLICATION_DIR" "$APP_URL" "$WEBSITE_NAME" "$APP_POOL_NAME" "${DISPLAY_NAME}" "${DEFAULT_DOC}" "" "" "${DOTNETVER}" "yes" "Web"
    !INSERTMACRO AvStandardUninstaller
!MACROEND

!ENDIF ;WEB_APP_IMPORT
