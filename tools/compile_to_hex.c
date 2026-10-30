#define MINISCHEME_NO_MAIN 1
/* Compiles Scheme source (the argument, or stdin with "-") to MSBC and prints it as hex.
 * For the newest firmware API by default: MSBC version 2 (a symbol table, API 1.9), inline
 * arithmetic (1.14), API procedures by number and inline car cdr not null? pair? eq?
 * vector-ref (1.15). --target-api X.Y compiles for older firmware (what it runs);
 * --no-inline-arith is --target-api 1.13; --msbc1 writes version 1 for firmware before 1.9.
 * Used by tools/build_apps.py and tools/board.py. */
#include "minischeme.h"
#include "minischeme_internal.h"
#include "msbc.h"
#include "compiler_msbc.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    char *source_text = NULL;
    const char *source_arg = NULL;
    uint16_t msbc_version = MSBC_VERSION;
    long target = 0;   /* major * 1000 + minor; 0: the compiler's own (the newest API) */
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--msbc1") == 0) msbc_version = 1, target = 1008;
        else if (strcmp(argv[i], "--no-inline-arith") == 0) target = 1013;
        else if (strcmp(argv[i], "--target-api") == 0 && i + 1 < argc) {
            char *end = NULL;
            long major = strtol(argv[++i], &end, 10);
            long minor = (end && *end == '.') ? strtol(end + 1, NULL, 10) : 0;
            target = major * 1000 + minor;
        } else if (!source_arg) source_arg = argv[i];
    }
    if (source_arg && strcmp(source_arg, "-") != 0) {
        source_text = vm_strdup(source_arg);
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

    if (target) {   /* the compiler reads *target-api* at each call (compiler.scm) */
        Value flag = mini_make_symbol(vm, "*target-api*");
        mini_push_root(vm, &flag);
        env_define(vm, vm->global_env, flag, mini_make_fixnum(target));
        mini_pop_root(vm);
    }

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
    if (!msbc_serialize_version(vm, code_val, &buf, &len, msbc_version)) {
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
