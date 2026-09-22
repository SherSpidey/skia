# Nex Skia m148 build scripts

This is a small adaptation of JetBrains' existing Skia release scripts for a
Google Skia `chrome/m148` checkout. It builds static libraries on GitHub-hosted
Windows and Linux runners. It does not integrate Skia into NexEngine.

## Provenance

The starting point is JetBrains/skia commit
`fc4d63be29654dcb972fa1642e54505aae3590cf` (tag `m148-fc4d63be29`):

- [build.py](https://github.com/JetBrains/skia/blob/fc4d63be29654dcb972fa1642e54505aae3590cf/tools/skia_release/build.py)
- [common.py](https://github.com/JetBrains/skia/blob/fc4d63be29654dcb972fa1642e54505aae3590cf/tools/skia_release/common.py)
- [archive.py](https://github.com/JetBrains/skia/blob/fc4d63be29654dcb972fa1642e54505aae3590cf/tools/skia_release/archive.py)
- [GitHub workflow](https://github.com/JetBrains/skia/blob/fc4d63be29654dcb972fa1642e54505aae3590cf/.github/workflows/build_for_skiko.yml)

`LICENSE.JetBrains-Skia` preserves that checkout's license. Skia and its bundled
dependencies retain their own licenses.

The dependency synchronization, Ninja invocation, command-line helpers, Windows
shell workaround, and archive structure follow those scripts. The build profile
is reduced to native Windows/Linux x64, without Skiko or GPU extension builds.

## Build profile

| Platform | Configuration | Compiler / runtime |
| --- | --- | --- |
| Windows x64 | Debug | clang-cl, MSVC dynamic debug CRT (`/MDd`) |
| Windows x64 | Release | clang-cl, MSVC dynamic release CRT (`/MD`) |
| Linux x64 | Debug | GCC 11, libstdc++ C++11 ABI (`_GLIBCXX_USE_CXX11_ABI=1`) |
| Linux x64 | Release | GCC 11, libstdc++ C++11 ABI (`_GLIBCXX_USE_CXX11_ABI=1`) |

- Skia libraries are static in all configurations. `/MD` and `/MDd` select the
  Windows C runtime; they do not make Skia a DLL.
- Windows CRT flags go into `extra_cflags`, covering both C and C++ sources.
- `is_trivial_abi=false` is retained for consumers using the MSVC ABI.
- Ganesh, Graphite, GL, Vulkan, Direct3D, Metal, and Dawn are disabled.
- PDF, HarfBuzz, and ICU are enabled. The upstream `skia` and `modules` targets
  retain the CPU path, text, and related module functionality. Skottie and tools
  are disabled. There is no hand-maintained list of individual Skia source files.
- Bundled dependencies follow the checkout's `DEPS`. The standard synchronization
  may download dependencies that the CPU build does not compile.
- Linux uses the runner's Fontconfig; this is not a fully self-contained Linux
  runtime bundle. Ubuntu 22.04 is the initial build baseline.

## Running and downloading

The companion workflow is `.github/workflows/build-nex-skia.yml`. Upload these
scripts before uploading the workflow. A commit changing the workflow or scripts
on `chrome/m148` or `nex/m148` starts the four build configurations automatically.

Enable Actions for the fork if GitHub asks. Manual `workflow_dispatch` additionally
requires the workflow to exist on the repository's default branch; the push
trigger does not require changing the default branch.

Each successful job uploads an artifact containing `Skia-*.zip`, retained for
30 days. Archives preserve the original directory structure: libraries, GN
arguments, and `nex-build-info.json` live under `out/<configuration>-<os>-x64/`;
headers remain under `include/`, `modules/`, and the other original paths.

On Windows, preserve `icudtl.dat` and deploy it beside the executable or DLL that
contains the linked ICU code when using ICU-backed functionality. Select Debug
libraries for a `/MDd` consumer and Release libraries for a `/MD` consumer. All
headers and libraries should come from the same build package.

The manifest records the source revision and GN arguments. Hosted runner tools
can change, so this is not a promise of byte-for-byte reproducible builds.

## Verification status

The draft's Python syntax, generated arguments for all four configurations, and
archive layout have been checked locally with synthetic inputs. A real Skia
compile has not been run for this draft. The first Actions run will validate the
actual compilation. Nex linking, rendering, font shaping, and PDF output remain
integration work; no extra integration test framework is included here.
