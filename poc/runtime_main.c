/*
 * Phase-3.1-Runtime: laedt das Original-Image an seiner echten Base, richtet
 * Stack und g_mem_base ein und fuehrt gelifteten Code aus -- die Speicher-
 * zugriffe (ADDR/MEM32) treffen damit die echten Programmstart-Daten.
 *
 * Ablauf:
 *   1. Das ORIGINAL Juiced.exe wird per image_loader.c gemappt. Bevorzugt an
 *      0x00400000; ist die VA durch DLL-ASLR belegt, an eine hohe Base. In
 *      beiden Faellen setzt g_mem_base = base - 0x400000, sodass ADDR(va)
 *      jede Gast-VA korrekt trifft.
 *   2. Stack als GAST-VA (HOST2GUEST), simulierte TIB via g_fs_base.
 *   3. Blattfunktionen mit absoluten Global-Zugriffen aufrufen und Ergebnis
 *      gegen den gemappten Speicher pruefen (Beweis: Speichermodell stimmt).
 *   4. Zuletzt den gelifteten Einstiegspunkt (EP 0x005CD316) aufrufen; er
 *      erreicht die ersten IAT-Importe (siehe logs/run_image.log). Die
 *      Import-Bridge ist der naechste Schritt.
 *
 * Der Host MUSS hoch gelinkt werden (-Wl,--image-base,0x10000000), sonst
 * kollidiert sein eigenes Image mit der Ziel-VA 0x00400000.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include "recomp_types.h"
#include "image_loader.h"

/* ---- globale Register-/FPU-/Runtime-Symbole (wie poc/main.c) ---- */
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

extern const recomp_dispatch_entry_t recomp_dispatch_table[];
extern const uint32_t recomp_dispatch_count;

recomp_func_t recomp_lookup(uint32_t va) {
    int lo = 0, hi = (int)recomp_dispatch_count - 1;
    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        uint32_t mva = recomp_dispatch_table[mid].address;
        if (mva == va) return recomp_dispatch_table[mid].func;
        if (mva < va) lo = mid + 1; else hi = mid - 1;
    }
    return NULL;
}
recomp_func_t recomp_lookup_manual(uint32_t va) { (void)va; return NULL; }
/* Bewusst NULL: unaufgeloeste Importe werden von RECOMP_ICALL mit VA+Caller
 * geloggt (Diagnose), ohne dass wir Stubs mit unbekanntem stdcall-argc bauen. */
recomp_func_t recomp_lookup_import(uint32_t va) { (void)va; return NULL; }
void recomp_dump_trace(const char *why) { (void)why; }

/* ---- Speicherlayout (Juiced.exe) ---- */
#define IMAGE_BASE     0x00400000u
#define IMAGE_HIGH     0x02144000u          /* Ende des belegten VA-Bereichs  */
#define STACK_BASE     0x00300000u
#define STACK_SIZE     0x00100000u          /* 1 MB                           */

static void* g_stack = NULL;

/* ---- VEH: Crash-Diagnose ---- */
static LONG WINAPI veh(EXCEPTION_POINTERS* ep) {
    if (ep->ExceptionRecord->ExceptionCode != EXCEPTION_ACCESS_VIOLATION)
        return EXCEPTION_CONTINUE_SEARCH;
    fprintf(stderr, "\n[CRASH] Access Violation at 0x%p\n",
            (void*)ep->ExceptionRecord->ExceptionAddress);
    if (ep->ExceptionRecord->NumberParameters >= 2)
        fprintf(stderr, "  %s @ 0x%p\n",
                ep->ExceptionRecord->ExceptionInformation[0] ? "WRITE" : "READ",
                (void*)ep->ExceptionRecord->ExceptionInformation[1]);
    fprintf(stderr, "  g_cur_func=0x%08X  EAX=0x%08X ECX=0x%08X EDX=0x%08X EBX=0x%08X\n",
            g_cur_func, g_eax, g_ecx, g_edx, g_ebx);
    fprintf(stderr, "  ESP=0x%08X ESI=0x%08X EDI=0x%08X EBP=0x%08X\n",
            g_esp, g_esi, g_edi, g_ebp);
    { int i; fprintf(stderr, "  letzte ICALLs:\n");
      for (i = 0; i < ICALL_TRACE_SIZE; i++) {
          uint32_t k = (g_icall_trace_idx - ICALL_TRACE_SIZE + i) & (ICALL_TRACE_SIZE - 1);
          if (g_icall_trace[k])
              fprintf(stderr, "    0x%08X <- 0x%08X\n", g_icall_trace[k], g_icall_from[k]);
      }
      fprintf(stderr, "  ICALLs gesamt: %u\n", g_icall_count); }
    fflush(stderr);
    return EXCEPTION_CONTINUE_SEARCH;
}

/* Host-Zeiger -> Gast-VA: ADDR() addiert g_mem_base, also muss ESP ein
 * GAST-VA sein, sonst zeigt ADDR(esp) neben das Mapping. 32-Bit-Wrap ist
 * beabsichtigt (g_mem_base ist der Rebase-Offset). */
#define HOST2GUEST(p) ((uint32_t)((uintptr_t)(p) - (uintptr_t)g_mem_base))

/* Simulierte TIB: die Runtime modelliert fs: ueber g_fs_base (Gast-VA). Der
 * SEH-Prolog des EP liest/schreibt fs:[0]; ohne TIB landet das bei ADDR(0). */
#define GUEST_TIB_VA 0x01030000u   /* freie Null-Region im gemappten Image */

static int setup_stack(void) {
    g_stack = VirtualAlloc((void*)(uintptr_t)STACK_BASE, STACK_SIZE,
                           MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
    if (!g_stack) {
        g_stack = VirtualAlloc(NULL, STACK_SIZE, MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
        if (!g_stack) { fprintf(stderr, "Stack-Alloc fehlgeschlagen\n"); return 0; }
        fprintf(stderr, "[warn] Stack bei %p (gewuenscht 0x%08X)\n", g_stack, STACK_BASE);
    }
    g_esp = HOST2GUEST((uintptr_t)g_stack + STACK_SIZE - 16);

    g_fs_base = GUEST_TIB_VA;
    MEM32(GUEST_TIB_VA + 0x00) = 0xFFFFFFFFu;                        /* SEH-Terminator */
    MEM32(GUEST_TIB_VA + 0x04) = HOST2GUEST((uintptr_t)g_stack + STACK_SIZE); /* StackBase  */
    MEM32(GUEST_TIB_VA + 0x08) = HOST2GUEST((uintptr_t)g_stack);              /* StackLimit */
    MEM32(GUEST_TIB_VA + 0x18) = GUEST_TIB_VA;                       /* Self          */
    return 1;
}

extern void sub_006C0E80(void);   /* mov eax,[0x72ad9c]; mov [0x76a090],eax; ret */
extern void sub_0040AC90(void);   /* fld dword [0x7019a8]; ret                    */
extern void sub_005CD316(void);   /* Einstiegspunkt (EP)                          */

int main(int argc, char** argv) {
    const char* exe = (argc > 1) ? argv[1] : "Juiced.exe";
    uint32_t span = 0, base = 0;
    static const uint32_t cand[] = { IMAGE_BASE, 0x30000000u, 0x50000000u, 0x60000000u, 0x10000000u };
    size_t ci;

    AddVectoredExceptionHandler(1, veh);
    printf("=== Juiced Phase-3.1-Runtime (Image + Stack + gelifteter Code) ===\n");

    for (ci = 0; ci < sizeof(cand) / sizeof(cand[0]); ci++) {
        span = recomp_load_image(exe, cand[ci]);
        if (span) { base = cand[ci]; break; }
    }
    if (!base) { fprintf(stderr, "FATAL: Image-Mapping fehlgeschlagen\n"); return 1; }
    /* Rebase-Fall: gelifteter Code rechnet jede GAST-VA ueber ADDR(va)=va+
     * g_mem_base, daher genuegt der Offset zwischen gewaehlter und echter Base. */
    g_mem_base = (ptrdiff_t)(int32_t)(base - IMAGE_BASE);
    printf("[*] Image '%s' -> Base 0x%08X (g_mem_base=0x%X), %u Bytes, VA 0x%08X..0x%08X\n",
           exe, base, (unsigned)g_mem_base, span, base, base + span);

    if (!setup_stack()) return 1;
    printf("[*] Stack: ESP=0x%08X   g_mem_base=%lld   Dispatch: %u Funktionen\n",
           g_esp, (long long)g_mem_base, recomp_dispatch_count);

    /* --- Test 1: Global-Read/Write (kein Call, keine Importe) --- */
    {
        uint32_t a = MEM32(0x0072AD9C);
        sub_006C0E80();
        uint32_t b = MEM32(0x0076A090);
        printf("[1] sub_006C0E80: [0x72AD9C]=0x%08X -> [0x76A090]=0x%08X  %s\n",
               a, b, (a == b) ? "OK" : "FEHLER");
    }

    /* --- Test 2: FPU-Global lesen (st0) --- */
    {
        float f;
        uint32_t raw = MEM32(0x007019A8);
        g_fp_top = 0;
        g_st[0] = 0.0;
        sub_0040AC90();
        memcpy(&f, &raw, 4);
        printf("[2] sub_0040AC90: [0x7019A8]=%g  st0=%.9g  fp_top=%d  %s\n",
               f, g_st[0], g_fp_top, ((float)g_st[0] == f) ? "OK" : "FEHLER");
    }

    /* --- Test 3: Einstiegspunkt (benoetigt aufgeloeste Importe) --- */
    printf("\n[3] EP 0x005CD316 aufrufen ...\n");
    fflush(stdout);
    sub_005CD316();
    printf("[3] EP zurueckgekehrt (ueberraschend vollstaendig).\n");

    return 0;
}
