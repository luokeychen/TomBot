#include <czmq.h>

int main() {
    zctx_t *ctx = zctx_new();
    assert(ctx);

    void* pub = zsocket_new(ctx, ZMQ_PUB);
    assert(pub);
    zsocket_connect(pub, "ipc:///tmp/publish.ipc");
    zclock_sleep(200);

    zmsg_t *msg = zmsg_new();
    assert(msg);
    int rc;
    rc = zmsg_addmem (msg, "tom?", 4);
    assert (rc == 0);
    rc = zmsg_addmem (msg, "123", 3);
    assert (rc == 0);
    rc = zmsg_addmem (msg, "456", 3);
    assert (rc == 0);
    zmsg_t *copy = zmsg_dup (msg);
    rc = zmsg_send (&copy, pub);
    assert (rc == 0);
    rc = zmsg_send (&msg, pub);
    assert(msg == NULL);
    assert(rc == 0);
    rc = zstr_send(pub, "hello");
    assert(rc == 0);
    zmsg_destroy(&msg);
    return 0;
}
