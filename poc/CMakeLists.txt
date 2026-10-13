cmake_minimum_required(VERSION 3.20)
project(JuicedRecomp VERSION 0.1.0 LANGUAGES C)

# =============================================================================
# VOLLBAU-Skelett (noch nicht ausgefuehrt - rechenschwer).
#
# Verifizierter PoC ist scripts\build_poc.cmd (eine TU, 32-Bit-Smoke-Link).
# Der Vollbau linkt alle 120 gelifteten TUs (zusammen ~772 MB C) und braucht
# daher viel Zeit/RAM; hier als Vorlage belassen.
#
# Wichtig: vor dem GCC-Build scripts\patch_recomp_weak.py anwenden (ADR E10).
# Toolchain: C:\msys64\mingw32 (i686-w64-mingw32), cmake, ninja.
# =============================================================================

set(CMAKE_C_STANDARD 17)

# Mechanisch gelifteter Code: Warnungen sind erwartbar; -O0 haelt Build-Zeiten
# beherrschbar. gc-sections verwirft nicht erreichbare Funktionen.
add_compile_options(-w -O0 -ffunction-sections -fdata-sections)
add_link_options(-Wl,--gc-sections)

if(NOT CMAKE_SIZEOF_VOID_P EQUAL 4)
    message(FATAL_ERROR "Juiced ist 32-bit: mit C:/msys64/mingw32/bin/gcc.exe bauen.")
endif()

set(ROOT "${CMAKE_CURRENT_SOURCE_DIR}/..")

file(GLOB GENERATED_SOURCES "${ROOT}/juiced_lifted/recomp_[0-9]*.c")
# Hinweis: recomp_dispatch.c und der echte Runtime-Einstieg (runtime/recomp32/main.c,
# an Juiced-Adressen angepasst) kommen im Vollbau dazu; main.c hier ist nur der PoC
# mit Stub-Dispatch und wuerde mit dem echten Dispatch kollidieren.

add_executable(juiced_recomp
    main.c
    ${GENERATED_SOURCES}
)

target_include_directories(juiced_recomp PRIVATE
    "${ROOT}/pcrecomp/runtime/recomp32"
    "${ROOT}/juiced_lifted"
)

# Das geliftete C erwartet die Funktions-Prototypen aus recomp_funcs.h.
target_compile_options(juiced_recomp PRIVATE -include "${ROOT}/juiced_lifted/recomp_funcs.h")
