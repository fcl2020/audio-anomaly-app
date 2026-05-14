[app]

title = 音频异常检测
package.name = audioanomaly
package.domain = org.audioanomaly
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0.0

# 关键修改：同时指定 hostpython3 和 python3 为同一版本
requirements = hostpython3==3.11.9,python3==3.11.9,kivy,numpy

orientation = portrait
fullscreen = 1
android.permissions = INTERNET,READ_EXTERNAL_STORAGE

android.api = 31
android.minapi = 24
android.ndk = 25b
android.arch = arm64-v8a
android.allow_backup = True
android.accept_sdk_license = True

[buildozer]

log_level = 2
warn_on_root = 1










