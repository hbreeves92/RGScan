[app]

# Application metadata
title = Rapidgator Scanner
package.name = rapidgatorscanner
package.domain = org.rapidgator.scanner

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt

version = 1.0.0

# Requirements - Kivy and standard library only
requirements = python3,kivy

# Android configuration
orientation = portrait

# Android permissions
android.permissions = INTERNET

# Android API settings
android.api = 31
android.minapi = 21
android.sdk = 31
android.ndk = 27c

# Build settings
fullscreen = 0

# Log settings
log_level = 2

# Android architecture - build for ARM (most devices) and ARM64
android.archs = arm64-v8a, armeabi-v7a

# Allow backup
android.allow_backup = 1


[buildozer]

log_level = 2
warn_on_root = 1
