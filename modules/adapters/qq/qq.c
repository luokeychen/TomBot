/**
 * @file   cli.c
 * @author mathslinux <riegamaths@gmail.com>
 * @date   Sat Jun 16 01:58:17 2012
 *
 * @brief  Command Line Interface for Lwqq
 *
 *
 */

#include <string.h>
#include <unistd.h>
#include <stdlib.h>
#include <getopt.h>
#include <signal.h>
#include <stdio.h>
#include <libgen.h>
#include <pthread.h>

#include "lwqq.h"

#include <czmq.h>

#ifdef WIN32
#include <windows.h>
#endif

#define LWQQ_CLI_VERSION "0.0.1"


static int list_f();
static int send_message(int type, const char* to, const char *content);

typedef int (*cfunc_t)(int argc, char **argv);

typedef struct CmdInfo {
	const char	*name;
	const char	*altname;
	cfunc_t		cfunc;
} CmdInfo;

static LwqqClient *lc = NULL;

static char *progname;

#ifdef WIN32
char *strtok_r(char *str, const char *delim, char **save)
{
    char *res, *last;

    if( !save )
        return strtok(str, delim);
    if( !str && !(str = *save) )
        return NULL;
    last = str + strlen(str);
    if( (*save = res = strtok(str, delim)) )
    {
        *save += strlen(res);
        if( *save < last )
            (*save)++;
        else
            *save = NULL;
    }
    return res;
}
const char* iconv(unsigned int from,unsigned int to,const char* str,size_t sz)
{
	static char buf[2048];
	wchar_t wbuf[2048];
	MultiByteToWideChar(from,0,str,-1,wbuf,sizeof(wbuf));
	WideCharToMultiByte(to,0,wbuf,-1,buf,sizeof(buf),NULL,NULL);
	return buf;
}
#define charset(str) iconv(CP_UTF8,CP_OEMCP,str,-1)
#else
#define charset(str) str
#endif

static int send_message(int type, const char* to, const char *data)
{
    LwqqMsg *msg = lwqq_msg_new(type);
    LwqqMsgMessage *mmsg = (LwqqMsgMessage*)msg;
    if (type == LWQQ_MS_DISCU_MSG) {
        msg->type = LWQQ_MS_DISCU_MSG;
        mmsg->discu.did = s_strdup(to);

    } else if (type == LWQQ_MS_GROUP_MSG) {
        msg->type = LWQQ_MS_GROUP_MSG;
        mmsg->group.group_code = s_strdup(to);

    }

    mmsg->super.to = s_strdup(to);
    mmsg->f_name = "微软雅黑";
    mmsg->f_size = 10;
    mmsg->f_style = 0;
    strcpy(mmsg->f_color,"000000");
    LwqqMsgContent * c = s_malloc(sizeof(*c));
    c->type = LWQQ_CONTENT_STRING;
    c->data.str = s_strdup(data);

    TAILQ_INSERT_TAIL(&mmsg->content,c,entries);

    LWQQ_SYNC_BEGIN(lc);
    lwqq_msg_send(lc,mmsg);
    LWQQ_SYNC_END(lc);

    mmsg->f_name = NULL;

    lwqq_msg_free(msg);
    return 0;
}

static LwqqErrorCode cli_login()
{
    LwqqErrorCode err;

    LWQQ_SYNC_BEGIN(lc);
    lwqq_login(lc,LWQQ_STATUS_ONLINE, &err);

    if (err != LWQQ_EC_OK) {
        goto failed;
    }

    LWQQ_SYNC_END(lc);
    return err;

failed:
    LWQQ_SYNC_END(lc);
    return LWQQ_EC_ERROR;
}

static void cli_logout(LwqqClient *lc)
{
    LwqqErrorCode err;

    lwqq_logout(lc, &err);
    if (err != LWQQ_EC_OK) {
/*        lwqq_log(LOG_DEBUG, "Logout failed\n");*/
    } else {
/*        lwqq_log(LOG_DEBUG, "Logout sucessfully\n");*/
    }
}

void signal_handler(int signum)
{
	if (signum == SIGINT || signum == SIGTERM) {
            cli_logout(lc);
            lwqq_client_free(lc);
            exit(0);
	}
}


//TODO 增加图片支持
static void* handle_pull_msg()
{
    zctx_t *ctx = zctx_new();
    void *pull = zsocket_new(ctx, ZMQ_PULL);
    zsocket_connect(pull, "ipc:///tmp/push.ipc");
    zclock_sleep(200);
    zmsg_t *msg = zmsg_new();
    zframe_t *frame = zframe_new(NULL, -1);

    char* content;
    char* id;
    char* type;
    int i_type;
    int i_id;

    while(1)
    {
        msg = zmsg_recv(pull);
        frame = zmsg_first(msg);
        content = zframe_strdup(frame);
        frame = zmsg_next(msg);
        id = zframe_strdup(frame);
        frame = zmsg_last(msg);
        type = zframe_strdup(frame);
        printf("receive message from engine: %s, %s, %s\n", content, id, type);
        i_type = atoi(type);
        printf("i_type: %d\n", i_type);
        i_id = atoi(id);
        if (i_type == LWQQ_MS_BUDDY_MSG) {
            send_message(LWQQ_MS_BUDDY_MSG, id, content);
        } else if (i_type == LWQQ_MS_DISCU_MSG)
            send_message(LWQQ_MS_DISCU_MSG, id, content);
        else if (i_type == LWQQ_MS_GROUP_MSG) {
            lwqq_msg_send_simple(lc, LWQQ_MS_GROUP_MSG, id, content);
            send_message(LWQQ_MS_GROUP_MSG, id, content);
        }
        else
            continue;
        
        free(content);
        free(id);
        free(type);
    }

    pthread_exit(NULL);
    return NULL;

}

static int list_f()
{
    char buf[1024] = {0};

    /* List all buddies */
    LwqqBuddy *buddy;
    LIST_FOREACH(buddy, &lc->friends, entries) {
        if (!buddy->uin) {
            /* BUG */
            return 0;
        }
        snprintf(buf, sizeof(buf), "uin:%s, ", buddy->uin);
        if (buddy->nick) {
            strcat(buf, "nick:");
            strcat(buf, buddy->nick);
            strcat(buf, ", ");
        }
        printf("Buddy info: %s\n", buf);
    }
    LwqqGroup *discu;
    LIST_FOREACH(discu, &lc->discus, entries) {
        if (!discu->did) {
            /* BUG */
            return 0;
        }
        snprintf(buf, sizeof(buf), "did:%s, ", discu->did);
        if (discu->name) {
            strcat(buf, "name:");
            strcat(buf, discu->name);
            strcat(buf, ", ");
        }
        printf("discu info: %s\n", buf);
    }

    LwqqGroup *group;
    LIST_FOREACH(group, &lc->groups, entries) {
        if (!group->gid) {
            /* BUG */
            return 0;
        }
        snprintf(buf, sizeof(buf), "gid:%s, ", group->gid);
        if (group->name) {
            strcat(buf, "name:");
            strcat(buf, group->name);
            strcat(buf, ", ");
        }
        printf("group info: %s\n", buf);
    }


    return 0;
}

static void handle_new_msg(LwqqRecvMsg *recvmsg)
{
    LwqqMsg *msg = recvmsg->msg;
    char buf[2048] = {0};
    zctx_t *ctx = zctx_new();
    void *pub = zsocket_new(ctx, ZMQ_PUB);
    zsocket_connect(pub, "ipc:///tmp/publish.ipc");
    zclock_sleep(200);
    zmsg_t *z_msg = zmsg_new();
    assert(msg);


    printf("Receive message type: %d\n", msg->type);
    if (msg->type == LWQQ_MS_BUDDY_MSG) {

        LwqqMsgContent *c;
        LwqqMsgMessage *mmsg = (LwqqMsgMessage*)msg;
        TAILQ_FOREACH(c, &mmsg->content, entries) {
            if (c->type == LWQQ_CONTENT_STRING) {
                strcat(buf, c->data.str);
            } else {
                printf ("Receive face msg: %d\n", c->data.face);
            }
        }
        printf("Receive message: %s\n", charset(buf));

        zmsg_addmem(z_msg, buf, strlen(buf));
        char* uin = mmsg->buddy.from->uin;
        zmsg_addmem(z_msg, uin, strlen(uin));
        char msg_type[5];
        sprintf(msg_type, "%d", LWQQ_MS_BUDDY_MSG);
        zmsg_addmem(z_msg, msg_type, strlen(msg_type));
        zmsg_send(&z_msg, pub);

    } else if (msg->type == LWQQ_MS_GROUP_MSG) {
        LwqqMsgMessage *mmsg = (LwqqMsgMessage*)msg;

        LwqqMsgContent *c;
        TAILQ_FOREACH(c, &mmsg->content, entries) {
            if (c->type == LWQQ_CONTENT_STRING) {
                strcat(buf, c->data.str);
            } else {
                printf ("Receive face msg: %d\n", c->data.face);
            }
        }
        printf("Receive message: %s\n", charset(buf));
        z_msg = zmsg_new();
        zmsg_addmem(z_msg, buf, strlen(buf));
        char* group_code = mmsg->group.group_code;
        zmsg_addmem(z_msg, group_code, strlen(group_code));
        char msg_type[5];
        sprintf(msg_type, "%d", LWQQ_MS_GROUP_MSG);
        zmsg_addmem(z_msg, msg_type, strlen(msg_type));
        zmsg_send(&z_msg, pub);
    } else if (msg->type == LWQQ_MS_DISCU_MSG) {
        LwqqMsgMessage *mmsg = (LwqqMsgMessage*)msg;

        LwqqMsgContent *c;
        TAILQ_FOREACH(c, &mmsg->content, entries) {
            if (c->type == LWQQ_CONTENT_STRING) {
                strcat(buf, c->data.str);
            } else {
                printf ("Receive face msg: %d\n", c->data.face);
            }
        }
        printf("Receive message: %s\n", charset(buf));
        z_msg = zmsg_new();
        zmsg_addmem(z_msg, buf, strlen(buf));
        char* did = mmsg->discu.did;
        zmsg_addmem(z_msg, did, strlen(did));
        char msg_type[5];
        sprintf(msg_type, "%d", LWQQ_MS_DISCU_MSG);
        zmsg_addmem(z_msg, msg_type, strlen(msg_type));
        zmsg_send(&z_msg, pub);
    } else if (msg->type == LWQQ_MT_STATUS_CHANGE) {
        LwqqMsgStatusChange *status = (LwqqMsgStatusChange*)msg;
        printf("Receive status change: %s - > %s\n",
               status->who,
               status->status);
    } else {
        printf("unknow message\n");
    }

    lwqq_msg_free(recvmsg->msg);
    zmsg_destroy(&z_msg);
    s_free(recvmsg);
}

static void *recvmsg_thread(void *list)
{
    LwqqRecvMsgList *l = (LwqqRecvMsgList *)list;

    /* Poll to receive message */
    lwqq_msglist_poll(l, 0);

    /* Need to wrap those code so look like more nice */
    while (1) {
        LwqqRecvMsg *recvmsg;
        pthread_mutex_lock(&l->mutex);
        if (TAILQ_EMPTY(&l->head)) {
            /* No message now, wait 100ms */
            pthread_mutex_unlock(&l->mutex);
            usleep(100000);
            continue;
        }
        recvmsg = TAILQ_FIRST(&l->head);
        TAILQ_REMOVE(&l->head,recvmsg, entries);
        pthread_mutex_unlock(&l->mutex);
        handle_new_msg(recvmsg);

	fflush(stdout);
    }

    pthread_exit(NULL);
    return NULL;
}

static void *info_thread(void *lc)
{
    LwqqErrorCode err;
    lwqq_info_get_friends_info(lc,NULL,&err);

    pthread_exit(NULL);
    return NULL;
}

static void need_verify2(LwqqClient* lc,LwqqVerifyCode* code)
{
    #ifdef WIN32
    const char *dir = NULL;

    #else
    const char *dir = "/tmp";
    #endif
    char fname[32];
    char vcode[256] = {0};
    snprintf(fname,sizeof(fname),"%s.jpeg",lc->username);

    lwqq_util_save_img(code->data,code->size,fname,dir);

/*    lwqq_log(LOG_NOTICE,"Need verify code to login, please check "*/
/*            "image file %s%s, and input below.\n",*/
/*            dir?:"",fname);*/
    printf("Verify Code:");
	fflush(stdout);
    scanf("%s",vcode);
    code->str = s_strdup(vcode);
    vp_do(code->cmd,NULL);
}
/**fix mingw and mintty and utf-8 no output */
static void log_direct_flush(int l,const char* str)
{
	fprintf(stderr,"%s\n",str);
	fflush(stderr);
}

static LwqqAction act = {
    .need_verify2 = need_verify2
};

int main()
{

    lwqq_log_redirect(log_direct_flush);

    char *qqnumber = "1744611347", *password = "jay19880821";
    LwqqErrorCode err;
    int i, c, e = 0;
    pthread_t tid[3];
    pthread_attr_t attr[3];

    progname = "test";

    const struct option long_options[] = {
        { "version", 0, 0, 'v' },
        { "help", 0, 0, 'h' },
        { "user", 0, 0, 'u' },
        { "pwd", 0, 0, 'p' },
        { 0, 0, 0, 0 }
    };

    signal(SIGINT, signal_handler);
    lwqq_log_set_level(4);
    lc = lwqq_client_new(qqnumber, password);
    lc->action = &act;
    if (!lc) {
/*        lwqq_log(LOG_NOTICE, "Create lwqq client failed\n");*/
        return -1;
    }

    /* Login to server */
    err = cli_login();
    if (err != LWQQ_EC_OK) {
/*        lwqq_log(LOG_ERROR, "Login error, exit\n");*/
        lwqq_client_free(lc);
        return -1;
    }

/*    lwqq_log(LOG_NOTICE, "Login successfully\n");*/
    LwqqAsyncEvset* set = lwqq_async_evset_new();
    LwqqAsyncEvent* ev;
    ev = lwqq_info_get_discu_name_list(lc);
    lwqq_async_evset_add_event(set,ev);
    LwqqErrorCode* error;
    ev = lwqq_info_get_group_name_list(lc, error);
    lwqq_async_evset_add_event(set,ev);

    /* Initialize thread */
    for (i = 0; i < 3; ++i) {
        pthread_attr_init(&attr[i]);
        pthread_attr_setdetachstate(&attr[i], PTHREAD_CREATE_DETACHED);
    }

    /* Create a thread to receive message */
    pthread_create(&tid[0], &attr[0], recvmsg_thread, lc->msg_list);

    /* Create a thread to update friend info */
    pthread_create(&tid[1], &attr[1], info_thread, lc);

    /* create a thread to get pulled message from robot */
    pthread_create(&tid[2], &attr[2], handle_pull_msg, NULL);
    list_f();


    /* Enter command loop  */
    zloop_t* zloop;
    zloop = zloop_new();
    zloop_start(zloop);

    /* Logout */
    cli_logout(lc);
    lwqq_client_free(lc);
    return 0;
}
