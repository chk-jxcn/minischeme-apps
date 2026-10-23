/**
 * @file msbc_to_fasl.c
 * @brief Boots an MSBC app on the PC and saves the result as a portable FASL.
 *
 *   msbc_to_fasl <app.msbc> <app.fasl>
 *
 * The app's top level runs on a VM set up like the firmware's (same libraries
 * and display geometry), then the heap is dumped in the portable 32-bit layout,
 * which the ESP32 and the WASM device load as /spiffs/app.fasl. Firmware-only
 * primitives the top level may call get stubs here; the snapshot names them
 * and the device binds its own at load time. Runs from any host width.
 *
 * Built against the firmware's runtime (minischeme-esp32 components/minischeme):
 *   gcc -O2 -I<esp32>/components/minischeme/include -Itools tools/msbc_to_fasl.c \
 *       <esp32>/components/minischeme/src/minischeme*.c -lm -o msbc_to_fasl
 */
#include "minischeme.h"
#include "minischeme_internal.h"
#include "minischeme_lib.h"
#include "minischeme_gui.h"
#include "minischeme_help.h"
#include "minischeme_device.h"
#include "minischeme_jsonfeed.h"
#include "msbc.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* (config-get key): no config.ini on the PC, so apps use their defaults */
static Value stub_config_get(MiniVM *vm, int argc, Value *argv) {
    (void)vm; (void)argc; (void)argv;
    return mini_false();
}

static Value stub_void(MiniVM *vm, int argc, Value *argv) {
    (void)vm; (void)argc; (void)argv;
    return mini_void();
}

int main(int argc, char **argv) {
    if (argc != 3) {
        fprintf(stderr, "usage: msbc_to_fasl <app.msbc> <app.fasl>\n");
        return 2;
    }
    FILE *fp = fopen(argv[1], "rb");
    if (!fp) {
        fprintf(stderr, "cannot open %s\n", argv[1]);
        return 1;
    }
    mini_gui_init_config(320, 480, MINI_GUI_MODE_BAND, 13, MINI_GUI_COLOR_RGB565);

    MiniConfig cfg;
    memset(&cfg, 0, sizeof(cfg));
    cfg.initial_heap_bytes = 256 * 1024;
    cfg.max_heap_bytes     = 256 * 1024;
    cfg.eden_bytes         = 4 * 1024;
    cfg.stack_size         = 1024;
    cfg.frame_capacity     = 256;
    cfg.skip_init_fasl     = true;
    MiniVM *vm = mini_create_ext(&cfg);
    if (!vm) {
        fclose(fp);
        fprintf(stderr, "cannot create the VM\n");
        return 1;
    }
    mini_register_hardware_lib(vm);
    mini_register_gui_lib(vm);
    mini_register_help_lib(vm);
    mini_register_device_lib(vm);
    mini_register_json_feed_lib(vm);
    mini_register_c_func(vm, "config-get", stub_config_get);
    mini_register_c_func(vm, "display-bench", stub_void);
    mini_register_c_func(vm, "tick-bench", stub_void);
    mini_register_c_func(vm, "mem-report", stub_void);

    Value code = msbc_deserialize_file(vm, fp);
    fclose(fp);
    if (!mini_get_error(vm) && mini_is_code(code)) {
        mini_push_root(vm, &code);
        Value clo = mini_make_closure(vm, code, mini_nil());
        mini_pop_root(vm);
        mini_push_root(vm, &clo);
        mini_vm_run(vm, clo, 0, NULL);
        mini_pop_root(vm);
    } else if (!mini_get_error(vm)) {
        vm_error(vm, "%s is not an MSBC image", argv[1]);
    }
    if (mini_get_error(vm)) {
        fprintf(stderr, "%s: %s\n", argv[1], mini_get_error(vm));
        mini_destroy(vm);
        return 1;
    }
    mini_gc(vm);
    size_t live = mini_get_allocated_bytes(vm);
    if (!mini_dump_fasl(vm, argv[2])) {
        fprintf(stderr, "%s: %s\n", argv[2], mini_get_error(vm) ? mini_get_error(vm) : "dump failed");
        mini_destroy(vm);
        return 1;
    }
    fp = fopen(argv[2], "rb");
    long size = 0;
    if (fp) {
        fseek(fp, 0, SEEK_END);
        size = ftell(fp);
        fclose(fp);
    }
    printf("%s: %ld bytes (portable 32-bit layout; host heap %u bytes)\n", argv[2], size, (unsigned)live);
    mini_destroy(vm);
    return 0;
}
