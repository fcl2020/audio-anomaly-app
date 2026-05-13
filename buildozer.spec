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
android.api = 33
android.minapi = 21
android.arch = arm64-v8a
android.allow_backup = True

[buildozer]

log_level = 2
warn_on_root = 1

