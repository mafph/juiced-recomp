import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;

import java.util.ArrayList;
import java.util.List;

/**
 * CleanupSections - markiert Nicht-Code-Sektionen als Daten.
 *
 * Entfernt alle Funktionen, deren Einstiegspunkt in den konfigurierten
 * Bereichen liegt, loescht dort die Disassemblierung und setzt einen
 * Plate-Kommentar. Daten (Sprungtabellen etc.) ausserhalb bleiben unberuehrt.
 *
 * Bereiche (Juiced.exe, ImageBase 0x400000):
 *   .securom      0xF93000 - 0x1030000
 *   unbenannt     0x1030000 - 0x2142000 (17 MB Nullen)
 */
public class CleanupSections extends GhidraScript {

    private static final long[][] RANGES = {
        { 0xF93000L, 0x1030000L },
        { 0x1030000L, 0x2142000L }
    };

    private static final String[] COMMENTS = {
        "SecuROM DRM-Stub - verschluesselt, kein Spielcode",
        "17-MB-Nullsektion - kein Code"
    };

    @Override
    public void run() throws Exception {
        FunctionManager fm = currentProgram.getFunctionManager();
        int before = fm.getFunctionCount();
        int removed = 0;

        for (int i = 0; i < RANGES.length; i++) {
            if (monitor.isCancelled()) {
                break;
            }
            Address start = toAddr(RANGES[i][0]);
            Address end = toAddr(RANGES[i][1] - 1);
            AddressSet set = new AddressSet(start, end);

            List<Function> toRemove = new ArrayList<>();
            for (Function f : fm.getFunctions(set, true)) {
                if (set.contains(f.getEntryPoint())) {
                    toRemove.add(f);
                }
            }
            for (Function f : toRemove) {
                removeFunction(f);
                removed++;
            }

            clearListing(start, end);
            setPlateComment(start, COMMENTS[i]);

            println("Bereich " + start + " - " + end + ": "
                    + toRemove.size() + " Funktionen entfernt");
        }

        int after = fm.getFunctionCount();
        println("Funktionen vorher: " + before);
        println("Funktionen entfernt: " + removed);
        println("Funktionen nachher: " + after);
    }
}
