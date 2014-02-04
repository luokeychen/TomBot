qq:
	clang -g -Ilwqq/build -Ilwqq/lib -Llwqq/build/lib -lzmq -lczmq -llwqq -lpthread qq.c -o qq
#         clang -fPIC -shared -Ilwqq/build -Ilwqq/lib -Llwqq/build/lib -lzmq -lczmq -llwqq -lpthread cli.c -o libqq.so
.PHONY: qq

clean:
	rm ./qq

