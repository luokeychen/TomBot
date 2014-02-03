libqq.so:
	clang -g -Ilwqq/build -Ilwqq/lib -Llwqq/build/lib -lzmq -lczmq -llwqq -lpthread cli.c -o qq
#         clang -fPIC -shared -Ilwqq/build -Ilwqq/lib -Llwqq/build/lib -lzmq -lczmq -llwqq -lpthread cli.c -o libqq.so
.PHONY: libqq.so

clean:
	rm ./cli.o
	rm ./libqq.so

