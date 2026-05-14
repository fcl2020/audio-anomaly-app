[app]

title = 音频异常检测
package.name = audioanomaly
package.domain = org.audioanomaly
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0.0

# 关键：锁定版本号，避免兼容性问题
requirements = python3==3.12.8,kivy==2.3.0,numpy==1.26.4,Cython==3.0.11

orientation = portrait
fullscreen = 1
android.permissions = INTERNET,READ_EXTERNAL_STORAGE

# numpy 要求 minapi >= 24
android.api = 31
android.minapi = 24
android.ndk = 25b
android.arch = arm64-v8a
android.allow_backup = True
android.accept_sdk_license = True

[buildozer]

log_level = 2
warn_on_root = 1








