#!/bin/sh
# Build the Xiaomi / Android TV app with the installed Android SDK. No Gradle.
# Usage: tv-app/build.sh 'https://karaoke.joshyfruit.com/tv'   (the TV link server.py prints)
set -eu
URL=${1:?usage: tv-app/build.sh 'https://<server>/tv'}
case $URL in
  http://*/tv|https://*/tv) ;;
  *) echo "Pass the TV link printed by server.py, like https://karaoke.joshyfruit.com/tv" >&2; exit 1 ;;
esac
SDK=${ANDROID_HOME:-$HOME/Library/Android/sdk}
BT=$(ls -d "$SDK"/build-tools/* | sort -V | tail -1)
JAR=$(ls "$SDK"/platforms/android-*/android.jar | sort -V | tail -1)
JDK=/opt/homebrew/opt/openjdk@21/bin
[ -x "$JDK/javac" ] || JDK=$(dirname "$(command -v javac)")
export PATH="$JDK:$PATH"  # apksigner and d8 need a modern Java, not the system Java 8

cd "$(dirname "$0")"
rm -rf build && mkdir -p build/assets build/classes
printf '%s\n' "$URL" > build/assets/url.txt
"$BT/aapt2" compile --dir res -o build/res.zip
"$BT/aapt2" link -o build/unsigned.apk -I "$JAR" --manifest AndroidManifest.xml \
  --min-sdk-version 23 --target-sdk-version 35 -A build/assets build/res.zip
javac -Xlint:-options --release 11 -classpath "$JAR" -d build/classes MainActivity.java
"$BT/d8" --lib "$JAR" --min-api 23 --output build $(find build/classes -name '*.class')
(cd build && zip -qj unsigned.apk classes.dex)
"$BT/zipalign" -pf 4 build/unsigned.apk build/aligned.apk

# Android's standard debug key, fine for sideloading your own app.
KS=$HOME/.android/debug.keystore
[ -f "$KS" ] || { mkdir -p "$HOME/.android"; keytool -genkeypair -keystore "$KS" -storepass android \
  -alias androiddebugkey -keypass android -keyalg RSA -validity 10000 -dname 'CN=Android Debug,O=Android,C=US'; }
"$BT/apksigner" sign --ks "$KS" --ks-pass pass:android --out karaoke-tv.apk build/aligned.apk
rm -f karaoke-tv.apk.idsig
echo "Built $(pwd)/karaoke-tv.apk"
