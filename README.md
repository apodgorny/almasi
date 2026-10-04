# Almasi

**A filesystem-native Python runtime for building and composing libraries.**

[Watch the 2-minute technical overview on YouTube](https://www.youtube.com/watch?v=eCk6kiAriR0&utm_source=chatgpt.com)

Almasi makes the **filesystem itself the structure of a Python library**.

Instead of maintaining separate registration, discovery, and integration layers, Almasi resolves components directly from the library's filesystem structure and exposes them through a native Python namespace.

The result is a development model where **the structure of the codebase becomes the structure of the runtime**.

## Core Ideas

### Library = Class

An Almasi library is a Python class.

Libraries can therefore be extended through ordinary Python inheritance:

```python
import a


class MyLib(a.A, path='/path/to/mylib/root'):

	def initialize(self):
		pass
```

Building a library on top of another library becomes native class inheritance.

### Filesystem → Namespace

A library's filesystem structure maps directly to its Python namespace:

```text
mylib/
└── root/
    ├── foo/
    │   ├── bar.py
    │   └── config.json
    └── README.txt
```

```python
import mylib

mylib.foo.bar
mylib.foo.config
mylib.README
```

Components are resolved lazily when accessed.

### Lazy Runtime Resolution

Almasi discovers components on demand:

```text
mylib.foo.bar
       │
       ▼
   filesystem
       │
       ▼
   resolve → load → cache
```

Python modules must inherit from `Module` to participate in the runtime:

```python
import mylib


class Bar(mylib.Module):

	def hello(self):
		print('Hello from Bar')
```

### Extensible Plugins

Filesystem resolution is separated from file semantics through a plugin system.

Plugins can define how different resource types are discovered and loaded:

```python
class Json(a.Plugin):

	EXTENSIONS = ('json',)

	def __call__(self, name, parent_path, parent_route):
		...
```

The runtime can therefore be extended without changing its core resolution model.

### Library Composition

Libraries remain ordinary Python modules and can be composed through normal imports:

```python
import mylib
import other_lib

mylib.foo
other_lib.bar
```

Each library maintains its own structure and namespace while participating in the same runtime model.

## CLI

Almasi includes a CLI for creating libraries and applications:

```bash
almasi lib my_lib a
almasi app my_app my_lib
```

The CLI scaffolds the filesystem structure and establishes the library inheritance chain automatically.

## Installation

Clone the repository and run the included installer:

```bash
git clone https://github.com/apodgorny/almasi
cd almasi
./install.sh
```

## Author

**Alexander Podgorny**

AI architect and systems researcher.

[LinkedIn](https://www.linkedin.com/in/podgorny/?utm_source=chatgpt.com)