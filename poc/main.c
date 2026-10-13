/*
 * Phase-3-PoC: 32-Bit-Link der pcrecomp-Runtime mit einer echten gelifteten TU.
 *
 * Stellt die globalen Register-/FPU-/Runtime-Symbole bereit, die der geliftete
 * Code aus recomp_types.h erwartet, und linkt gegen recomp_0000.c. Es wird
 * absichtlich KEIN Spielcode ausgefuehrt (kein Speicher-Layout/Imports) -- der
 * PoC belegt nur, dass Toolchain + Runtime + Lift ein 32-Bit-PE ergeben.
 *
 * Nicht aufgeloeste Symbole (sub_* in anderen TUs, Imports) werden beim Link
 * ueber generierte weak-Leer-Stubs geschlossen (scripts/gen_weak_stubs.py);
 * im Vollbau kommen sie aus den uebrigen recomp_*.c bzw. dem Import-Bridge.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include "recomp_types.h"

uint32_t g_eax, g_ecx, g_edx, g_esp, g_ebx, g_esi, g_edi, g_ebp;
double   g_st[8];
int      g_fp_top;
uint16_t g_fpu_cw = 0x027F;
uint16_t g_seg_cs, g_seg_ds, g_seg_es, g_seg_fs, g_seg_gs, g_seg_ss;
uint32_t g_fs_base, g_gs_base, g_cur_func;
uint64_t g_mm[8];
xmm_t    g_xmm[8];
uint32_t g_mxcsr = 0x1F80;
ptrdiff_t g_mem_base = 0;
uint32_t g_icall_trace[ICALL_TRACE_SIZE] = {0};
uint32_t g_icall_from[ICALL_TRACE_SIZE] = {0};
uint32_t g_icall_trace_idx = 0;
uint32_t g_icall_count = 0;

recomp_func_t recomp_lookup(uint32_t va)        { (void)va; return NULL; }
recomp_func_t recomp_lookup_manual(uint32_t va) { (void)va; return NULL; }
recomp_func_t recomp_lookup_import(uint32_t va) { (void)va; return NULL; }
void recomp_dump_trace(const char *why)         { (void)why; }

const recomp_dispatch_entry_t recomp_dispatch_table[1] = { { 0, NULL } };
const uint32_t recomp_dispatch_count = 0;

extern void sub_00401000(void);

int main(void) {
    recomp_func_t entry = sub_00401000;
    printf("[poc] juiced recomp 32-bit link OK\n");
    printf("[poc] sub_00401000 @ %p\n", (void *)entry);
    printf("[poc] sizeof(void*)=%u\n", (unsigned)sizeof(void *));
    return 0;
}
