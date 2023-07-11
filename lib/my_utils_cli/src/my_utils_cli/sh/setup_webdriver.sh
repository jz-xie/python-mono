#!/bin/bash

# Download the latest version of Google Chrome for Linux
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb

# Install Google Chrome
sudo apt-get update
sudo apt-get install -y ./google-chrome-stable_current_amd64.deb

# Install X Sever
sudo apt-get install xvfb

# Get the version of Google Chrome
chrome_version=$(google-chrome --version | awk '{print $3}' | cut -d '.' -f 1-3)

# Download the corresponding version of ChromeDriver for Linux
wget https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${chrome_version}
wget https://chromedriver.storage.googleapis.com/$(cat LATEST_RELEASE_${chrome_version})/chromedriver_linux64.zip

# Unzip ChromeDriver
unzip chromedriver_linux64.zip

# Move ChromeDriver to /usr/local/bin
sudo mv chromedriver /usr/local/bin/

# Clean up
rm google-chrome-stable_current_amd64.deb LATEST_RELEASE_${chrome_version} chromedriver_linux64.zip LICENSE.chromedriver
