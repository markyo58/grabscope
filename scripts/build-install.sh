#!/bin/zsh
# Build GrabScope Release with Crystal's Xcode and install to /Applications.
# Signing: the Accessibility grant (TCC) is keyed to the code requirement. Plain ad-hoc (-s -) pins the
# code hash, so every rebuild loses the grant. Two stable routes:
#   SIGN_ID="<identity name>"  a real or self-signed code-signing identity (none exists on this Mac today)
#   default                    ad-hoc with a FIXED designated requirement (identifier only)
# ponytail: the fixed-DR route is UNTESTED against TCC; if the grant is still lost after a rebuild,
# create one self-signed identity (Keychain Access > Certificate Assistant) and pass SIGN_ID.
set -euo pipefail
cd ${0:A:h}/..
export DEVELOPER_DIR=/Volumes/Crystal/Applications/Xcode.app/Contents/Developer
xcodebuild -project GrabScope.xcodeproj -scheme GrabScope -configuration Release -derivedDataPath build \
  CODE_SIGN_IDENTITY=- CODE_SIGNING_ALLOWED=YES CODE_SIGN_ENTITLEMENTS= DEVELOPMENT_TEAM= \
  CODE_SIGN_STYLE=Manual ENABLE_HARDENED_RUNTIME=NO build | tail -3
app=build/Build/Products/Release/GrabScope.app
if [[ -n "${SIGN_ID:-}" ]]; then
  codesign --force --deep -s "$SIGN_ID" $app
else
  codesign --force --deep -s - -r='designated => identifier "uk.arc.grabscope"' $app
fi
osascript -e 'tell application "GrabScope" to quit' 2>/dev/null || true
sleep 2
ditto $app /Applications/GrabScope.app
open /Applications/GrabScope.app
echo "installed; requirement: $(codesign -d -r- /Applications/GrabScope.app 2>&1 | tail -1)"
