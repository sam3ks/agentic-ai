@echo off
echo Setting SSL certificate verification settings...

REM Disable Python HTTPS verification
set PYTHONHTTPSVERIFY=0

REM Clear certificate bundle paths for requests and curl
set REQUESTS_CA_BUNDLE=
set CURL_CA_BUNDLE=

echo Environment variables set:
echo PYTHONHTTPSVERIFY=0
echo REQUESTS_CA_BUNDLE=
echo CURL_CA_BUNDLE=

echo.
echo WARNING: Disabling SSL certificate verification reduces security.
echo Only use this in development environments behind corporate firewalls.
echo.

REM If a script name is provided as parameter, run it
if not "%~1"=="" (
    echo Running: python %*
    python %*
) else (
    echo To run a Python script with these settings, use:
    echo ssl_fix.bat run_loan_cli.py
    echo.
)
