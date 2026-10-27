#!/bin/sh
# Rebuild downloads/submittal-register.zip from the skill folder. Run from the repo root after any change to submittal-register/.
set -e
rm -f downloads/submittal-register.zip
zip -qr downloads/submittal-register.zip submittal-register -x "*/__pycache__/*"
echo "Built downloads/submittal-register.zip"
