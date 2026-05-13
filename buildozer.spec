[app]

title = 音频异常检测
package.name = audioanomaly
package.domain = org.audioanomaly
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0.0
requirements = python3,kivy,numpy,scipy,PyWavelets
orientation = portrait
fullscreen = 1
android.permissions = INTERNET,READ_EXTERNAL_STORAGE

# 关键：使用 NDK 28c 和 API 31，minapi 24
android.api = 31
android.minapi = 24
android.ndk = 28c
android.arch = arm64-v8a
android.allow_backup = True
android.accept_sdk_license = True

[buildozer]

log_level = 2
warn_on_root = 1






