#!/bin/bash

# Get the version of Google Chrome
chrome_version=$(google-chrome --version | awk '{print $3}' | cut -d '.' -f 1-3)

# Remove ChromeDriver from /usr/local/bin
sudo rm /usr/local/bin/chromedriver

# Remove Google Chrome
sudo apt-get remove -y google-chrome-stable

# Remove the downloaded files
rm google-chrome-stable_current_amd64.deb LATEST_RELEASE_${chrome_version} chromedriver_linux64.zip
