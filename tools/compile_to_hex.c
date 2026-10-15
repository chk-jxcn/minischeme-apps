#define MINISCHEME_NO_MAIN 1
/* Compiles Scheme source (argv[1], or stdin with "-") to MSBC and prints it as hex. Used by tools/build_apps.py and tools/bench_board.py. */
#include "minischeme.h"
#include "minischeme_internal.h"
#include "msbc.h"
#include "compiler_msbc.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    char *source_text = NULL;
    if (argc >= 2 && strcmp(argv[1], "-") != 0) {
        source_text = vm_strdup(argv[1]);
    } else {
        size_t cap = 65536;
        size_t len = 0;
        source_text = (char *)malloc(cap);
        if (!source_text) return 1;
        int c;
        while ((c = getchar()) != EOF) {
            if (len + 2 >= cap) {
                cap *= 2;
                source_text = (char *)realloc(source_text, cap);
                if (!source_text) return 1;
            }
            source_text[len++] = (char)c;
        }
        source_text[len] = '\0';
    }
    if (!source_text) return 1;

    MiniConfig comp_cfg;
    memset(&comp_cfg, 0, sizeof(comp_cfg));
    comp_cfg.eden_bytes = 4 * 1024 * 1024;
    comp_cfg.initial_heap_bytes = 16 * 1024 * 1024;
    comp_cfg.skip_init_fasl = true;
    MiniVM *vm = mini_create_ext(&comp_cfg);
    if (!vm) {
        free(source_text);
        return 1;
    }

    Value comp_code = msbc_deserialize(vm, compiler_msbc_data, compiler_msbc_len);
    Value comp_clo = mini_make_closure(vm, comp_code, mini_nil());
    mini_vm_run(vm, comp_clo, 0, NULL);

    Value helper = env_lookup_name(vm, "%compile-source-to-code");
    Value s = mini_make_string(vm, source_text);
    free(source_text);
    Value code_val = mini_call(vm, helper, 1, &s);
    if (vm->has_error || !mini_is_code(code_val)) {
        fprintf(stderr, "Compile error: %s (returned value: ", vm->has_error ? vm->error_buf : "not code");
        mini_print_value(vm, code_val, stderr, true);
        fprintf(stderr, ")\n");
        mini_destroy(vm);
        return 1;
    }

    uint8_t *buf = NULL;
    size_t len = 0;
    if (!msbc_serialize(vm, code_val, &buf, &len)) {
        fprintf(stderr, "Serialization error\n");
        mini_destroy(vm);
        return 1;
    }

    for (size_t i = 0; i < len; i++) {
        printf("%02x", buf[i]);
    }
    printf("\n");

    free(buf);
    mini_destroy(vm);
    return 0;
}
