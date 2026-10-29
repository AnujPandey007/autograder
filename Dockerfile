FROM gcc:14-bookworm
WORKDIR /work
ENV LC_ALL=C
ENV ASAN_OPTIONS=detect_leaks=0:halt_on_error=1
ENV UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=0
