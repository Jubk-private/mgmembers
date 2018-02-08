@ECHO OFF

call REM set root dir
set DJANGOPROJECT_ROOT_DIR=%~dp0%

REM load virtual env
call "%DJANGOPROJECT_ROOT_DIR%python-env\Scripts\activate"

REM tell django which file to use for settings
SET DJANGO_SETTINGS_MODULE=mgmembers_site.settings

python manage.py runserver 0.0.0.0:7000
