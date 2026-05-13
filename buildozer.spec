[app]

title = 音频异常检测
package.name = audioanomaly
package.domain = org.audioanomaly
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0.0
requirements = python3,kivy,numpy
orientation = portrait
fullscreen = 1
android.permissions = INTERNET,READ_EXTERNAL_STORAGE

# 关键改动：minapi 从 21 提到 24，满足 numpy 要求
android.api = 31
android.minapi = 24
android.ndk = 25b
android.arch = arm64-v8a
android.allow_backup = True
android.accept_sdk_license = True

[buildozer]

log_level = 2
warn_on_root = 1





