CC = gcc
CFLAGS = -Wall -O2 -fPIC
DEBUG_FLAGS = -Wall -g

# Default target: build the shared library
all: libtexteditor.so

# Build shared library (Linux)
libtexteditor.so: text_editor.c text_editor.h
		$(CC) -shared $(CFLAGS) text_editor.c -o libtexteditor.so

# Build shared library (macOS)
libtexteditor.dylib: text_editor.c text_editor.h
		$(CC) -dynamiclib $(CFLAGS) text_editor.c -o libtexteditor.dylib

# Run tests
test: libtexteditor.so
		python3 checker.py

# Clean build artifacts
clean:
		rm -f libtexteditor.so libtexteditor.dylib *.o
		rm -rf test_artifacts/*/outputs

.PHONY: all test test-perf debug clean
