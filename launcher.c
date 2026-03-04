/*
 * La Mia Scribe — Native macOS launcher
 *
 * This launcher uses the Python.app framework executable which properly
 * registers with the macOS WindowServer for GUI apps.
 */
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>

int main(int argc, char *argv[]) {
    /*
     * Use the Python.app framework binary — this is the "pythonw" equivalent
     * that registers with the macOS window server properly.
     */
    const char *python_gui = "/Library/Frameworks/Python.framework/Versions/3.14/Resources/Python.app/Contents/MacOS/Python";
    const char *python_fallback = "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3";
    const char *app_dir = "/Users/roccocatrone/la-mia-scribe";
    const char *python;

    /* Prefer Python.app for proper GUI registration */
    if (access(python_gui, X_OK) == 0) {
        python = python_gui;
    } else if (access(python_fallback, X_OK) == 0) {
        python = python_fallback;
    } else {
        return 1;
    }

    chdir(app_dir);

    /* exec replaces this process with Python — the window server
     * sees the process as the .app bundle's process */
    char *new_argv[] = { (char *)python, "launch_wrapper.py", NULL };
    execv(python, new_argv);

    return 1;
}
