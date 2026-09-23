#! /usr/bin/env python3

import json
import os
import shutil
import subprocess
import sys
import time

import common


def git_sync_with_retries(skia_dir, max_retries=3, backoff_seconds=5):
  attempt = 0
  while True:
    try:
      print("> Running tools/git-sync-deps (attempt {}/{})".format(attempt + 1, max_retries + 1))
      env = os.environ.copy()
      env['GIT_SYNC_DEPS_SKIP_EMSDK'] = '1'
      subprocess.check_call([sys.executable, "tools/git-sync-deps"], cwd=skia_dir, env=env)
      print("Success")
      return
    except subprocess.CalledProcessError as error:
      attempt += 1
      if attempt > max_retries:
        print("All {} retries failed. Giving up.".format(max_retries))
        raise
      wait = backoff_seconds * attempt
      print(f"Failed (exit {error.returncode}), retrying in {wait}s...")
      time.sleep(wait)


def patch_windows_toolchain(skia_dir):
  toolchain_path = skia_dir / "gn" / "toolchain" / "BUILD.gn"
  with toolchain_path.open("r", encoding="utf-8") as toolchain_file:
    contents = toolchain_file.read()

  patched = contents.replace(
      'shell = "cmd.exe /c',
      'shell = "cmd.exe /v:on /c',
  ).replace(
      r'env_setup = "$shell set \"PATH=%PATH%',
      r'env_setup = "$shell set \"PATH=!PATH!',
  )

  if patched != contents:
    with toolchain_path.open("w", encoding="utf-8") as toolchain_file:
      toolchain_file.write(patched)


def prepare_skia_checkout(skia_dir):
  print("> Running tools/git-sync-deps")
  git_sync_with_retries(skia_dir)

  print("> Fetching ninja")
  subprocess.check_call([sys.executable, "bin/fetch-ninja"], cwd=skia_dir)

  if common.host() == 'windows':
    patch_windows_toolchain(skia_dir)


def ninja_path(host):
  return os.path.join('third_party', 'ninja', 'ninja.exe' if host == 'windows' else 'ninja')


def main():
  skia_dir = common.skia_dir()
  os.chdir(skia_dir)
  build_type = common.build_type()
  machine = common.machine()
  host = common.host()
  target = common.target()

  if target not in ('windows', 'linux') or target != host or machine != 'x64':
    raise ValueError('This Nex configuration supports native Windows/Linux x64 builds only')
  if build_type not in ('Debug', 'Release'):
    raise ValueError('build-type must be Debug or Release')
  if (common.enable_graphite() or
      common.enable_graphite_dawn() or
      common.gpu_as_extension()):
    raise ValueError('This Nex configuration does not support Graphite, Dawn, or GPU extensions')

  milestone = (skia_dir / 'include/core/SkMilestone.h').read_text(encoding='utf-8')
  if '#define SK_MILESTONE 148' not in milestone:
    raise ValueError('These build settings are prepared for Skia m148')

  prepare_skia_checkout(skia_dir)
  if build_type == 'Debug':
    args = ['is_debug=true', 'is_official_build=false']
  else:
    args = ['is_debug=false', 'is_official_build=true']

  args += [
      'target_cpu="' + machine + '"',
      'is_component_build=false',
      'is_trivial_abi=false',
      'skia_use_system_expat=false',
      'skia_use_system_libjpeg_turbo=false',
      'skia_use_system_libpng=false',
      'skia_use_system_libwebp=false',
      'skia_use_system_zlib=false',
      'skia_use_system_freetype2=false',
      'skia_use_system_harfbuzz=false',
      'skia_pdf_subset_harfbuzz=true',
      'skia_use_system_icu=false',
      'skia_use_harfbuzz=true',
      'skia_use_icu=true',
      'skia_enable_pdf=true',
      'skia_enable_skottie=false',
      'skia_enable_tools=false',
      'skia_enable_ganesh=true',
      'skia_enable_optimize_size=false',
      'skia_enable_graphite=false',
      'skia_use_gl=false',
      'skia_use_vulkan=false',
      'skia_use_direct3d=false',
      'skia_use_metal=false',
      'skia_use_dawn=false',
      'extra_cflags=[]',
      'extra_cflags_cc=[]',
  ]

  if target == 'linux':
    args += [
        'extra_cflags_cc+=["-fno-exceptions", "-fno-rtti", "-D_GLIBCXX_USE_CXX11_ABI=1"]',
        'cc="gcc-11"',
        'cxx="g++-11"',
    ]
    runtime = 'libstdc++ ABI=1'
  else:
    clang_path = shutil.which('clang-cl.exe')
    if not clang_path:
      raise RuntimeError('clang-cl.exe must be on PATH')
    runtime = 'MDd' if build_type == 'Debug' else 'MD'
    clang_dir = os.path.dirname(os.path.dirname(clang_path)).replace('\\', '/')
    args += [
        'clang_win="' + clang_dir + '"',
        'extra_cflags+=["/' + runtime + '", "-DSK_FONT_HOST_USE_SYSTEM_SETTINGS"]',
    ]

  out = os.path.join('out', build_type + '-' + target + '-' + machine)
  gn = 'gn.exe' if host == 'windows' else 'gn'
  subprocess.check_call([os.path.join('bin', gn), 'gen', out, '--args=' + ' '.join(args)])
  subprocess.check_call([ninja_path(host), '-C', out, '-j', str(min(4, os.cpu_count() or 2)), 'skia', 'modules'])

  info = {
      'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
      'milestone': 148,
      'build_type': build_type,
      'target': target,
      'machine': machine,
      'runtime': runtime,
      'gn_args': args,
      'based_on': 'JetBrains/skia@fc4d63be29654dcb972fa1642e54505aae3590cf',
  }
  (skia_dir / out / 'nex-build-info.json').write_text(json.dumps(info, indent=2) + '\n', encoding='utf-8')
  return 0


if __name__ == '__main__':
  sys.exit(main())
