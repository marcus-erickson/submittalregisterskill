#!/bin/sh
# Rebuild the downloads from the skill folders. Run from the repo root after any change to
# submittal-register/ or submittal-intake/.
#
#   downloads/submittal-register.zip  the register skill as is
#   downloads/submittal-intake.zip    the intake skill plus the few register scripts it uses,
#                                     so it installs on its own
set -e
mkdir -p downloads

rm -f downloads/submittal-register.zip
zip -qr downloads/submittal-register.zip submittal-register -x "*/__pycache__/*"
echo "Built downloads/submittal-register.zip"

STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
cp -r submittal-intake "$STAGE/submittal-intake"
mkdir -p "$STAGE/submittal-intake/register-scripts" "$STAGE/submittal-intake/examples"
for f in build_register.py register_model.py columns.py columns.default.json; do
  cp "submittal-register/scripts/$f" "$STAGE/submittal-intake/register-scripts/$f"
done
cp -r submittal-register/scripts/adapters "$STAGE/submittal-intake/register-scripts/adapters"
cp submittal-register/examples/columns-tracking.json "$STAGE/submittal-intake/examples/columns-tracking.json"
rm -f downloads/submittal-intake.zip
(cd "$STAGE" && zip -qr "$OLDPWD/downloads/submittal-intake.zip" submittal-intake -x "*/__pycache__/*")
echo "Built downloads/submittal-intake.zip"
