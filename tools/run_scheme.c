#define MINISCHEME_NO_MAIN 1
/* Compiles Scheme source (stdin) as tools/compile_to_hex.c does, then runs the
 * bytecode in a fresh VM configured like the device's (no init.scm) and lets it
 * print with display / write. Exit status 0, or 2 with the error on stderr when
 * the program fails. Used by tests/test_applib.py: the app library's own tests. */
#include "minischeme.h"
#include "minischeme_internal.h"
#include "msbc.h"
#include "compiler_msbc.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char *read_stdin(void) {
    size_t cap = 65536, len = 0;
    char *text = (char *)malloc(cap);
    if (!text) return NULL;
    int c;
    while ((c = getchar()) != EOF) {
        if (len + 2 >= cap) {
            char *bigger = (char *)realloc(text, cap * 2);
            if (!bigger) {
                free(text);
                return NULL;
            }
            text = bigger;
            cap *= 2;
        }
        text[len++] = (char)c;
    }
    text[len] = '\0';
    return text;
}

int main(void) {
    char *source_text = read_stdin();
    if (!source_text) return 1;

    MiniConfig comp_cfg;
    memset(&comp_cfg, 0, sizeof(comp_cfg));
    comp_cfg.eden_bytes = 4 * 1024 * 1024;
    comp_cfg.initial_heap_bytes = 16 * 1024 * 1024;
    comp_cfg.skip_init_fasl = true;
    MiniVM *cvm = mini_create_ext(&comp_cfg);
    if (!cvm) {
        free(source_text);
        return 1;
    }
    Value comp_code = msbc_deserialize(cvm, compiler_msbc_data, compiler_msbc_len);
    Value comp_clo = mini_make_closure(cvm, comp_code, mini_nil());
    mini_vm_run(cvm, comp_clo, 0, NULL);
    Value helper = env_lookup_name(cvm, "%compile-source-to-code");
    Value s = mini_make_string(cvm, source_text);
    free(source_text);
    Value code_val = mini_call(cvm, helper, 1, &s);
    if (cvm->has_error || !mini_is_code(code_val)) {
        fprintf(stderr, "Compile error: %s\n", cvm->has_error ? cvm->error_buf : "not code");
        mini_destroy(cvm);
        return 2;
    }
    uint8_t *buf = NULL;
    size_t len = 0;
    if (!msbc_serialize(cvm, code_val, &buf, &len)) {
        fprintf(stderr, "Serialization error\n");
        mini_destroy(cvm);
        return 2;
    }
    mini_destroy(cvm);

    MiniConfig run_cfg;
    memset(&run_cfg, 0, sizeof(run_cfg));
    run_cfg.eden_bytes = 1024 * 1024;
    run_cfg.initial_heap_bytes = 8 * 1024 * 1024;
    run_cfg.skip_init_fasl = true;
    run_cfg.enable_stack_trace = true;
    MiniVM *vm = mini_create_ext(&run_cfg);
    if (!vm) {
        free(buf);
        return 1;
    }
    Value code = msbc_deserialize(vm, buf, len);
    free(buf);
    Value clo = mini_make_closure(vm, code, mini_nil());
    mini_vm_run(vm, clo, 0, NULL);
    fflush(stdout);
    int status = 0;
    if (vm->has_error) {
        fprintf(stderr, "Error: %s\n", vm->error_buf);
        status = 2;
    }
    mini_destroy(vm);
    return status;
}
