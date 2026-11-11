# Architecture: Forked Runtime Namespaces

**Status:** Implemented in Almasi.  
**Scope:** In-process Python library forks; not application process isolation or persistent-storage cloning.

## 1. Purpose

An Almasi library is a filesystem-backed Python namespace. Ordinarily, each library has one canonical runtime instance, and its lazily resolved Python components are cached within that instance.

**A fork gives the same source library another independent runtime identity.** It keeps the filesystem and reusable compiled code, but gives loaded Python modules, classes, services, and namespace caches their own state.

> One source tree; multiple separately evolving runtime worlds.

This is a library mechanism, not an ontology or database mechanism. The consuming library decides what starting, stopping, persisting, or copying a world means.

## 2. Structural model

```text
                    canonical library: mylib
                     source tree / root/
                              |
                +-------------+-------------+
                |             |             |
             default         alice          bob
             (mylib)        (fork)         (fork)
                |             |             |
             module A      module A'     module A''
             class A       class A'      class A''
             service S     service S'    service S''
             cache D       cache A      cache B
                \             |             /
                 same Python source files
```

The canonical library and forks share physical source files, their inherited filesystem structure, and the compiled source-code cache. Each fork has its own namespace face, child/carrier cache, plugin instances, and fork-loaded module globals. Classes and service singletons materialized through different forks have distinct Python identities.

Almasi does **not** copy a live object graph or duplicate a database when a fork is constructed.

## 3. Public API

```python
import mylib

alice = mylib.fork('alice')
bob   = mylib.fork('bob')

assert mylib['default'] is mylib
assert mylib['alice'] is alice
assert mylib['bob'] is bob
assert alice is not bob
```

- `library.fork(name)` creates a new fork, returns its library face, and registers it under `name` on the **source face**.
- `library[name]` looks up a previously registered fork; it does not create one. `library['default']` returns that library face itself.
- A generic Almasi fork name must be a nonempty string other than `'default'`.
- Calling generic `library.fork(name)` again with a registered name raises `ValueError`. A library may deliberately override this policy; O does so.
- Forks can themselves be forked: `alice.fork('child')` creates a child registered on `alice`. Names are scoped to the source face.

Do not use generic fork names as filesystem paths: the base validation is for runtime names, not for storage-directory safety.

## 4. How a fork is built

At creation, `A.fork()`:

1. Allocates another instance of the same library class, without publishing a second canonical library module.
2. Deep-copies ordinary public, non-callable configuration that has not been cached as a resolved namespace component.
3. Starts with fresh `__children__`, `__cached_names__`, and nested `__forks__` registries.
4. Creates fresh plugin instances and a fork-aware Python import environment.
5. Records `__fork_source__` and `__fork_name__`, then registers the fork on its source face.

Resolved classes, service instances, bound methods, and callable runtime state are **not** copied from the canonical library. Components are resolved and created separately in each fork when requested.

A fork is therefore not the same operation as `extend()`. `extend()` defines and publishes a canonical library class with a filesystem/inheritance lineage; `fork()` creates a detached runtime instance of an existing library.

## 5. Import and loading semantics

When a Python component is loaded through a fork, its module executes with a fork-aware `__import__` for that library's name and inherited library names:

```python
# In a Python component loaded through alice:
import mylib

# mylib resolves to the alice fork in this module.
```

The normal `import mylib` performed by external application code remains the canonical library. Application code selects a fork explicitly, for example via `mylib['alice']`.

The loader assigns fork-specific module identities in `sys.modules` and reuses compiled code objects without reusing each module's global namespace. Other, unrelated imports keep normal Python behavior. This is targeted library isolation, **not** isolation of all Python process globals, external packages, or the operating system.

Filesystem lookup and inherited library resolution still use the existing library source tree. The fork owns its own resolved component cache.

## 6. Service identity and lifecycle

Services are singletons per loaded service class. Fork-specific class loading therefore gives each fork its own service instance.

However, a function or method already bound to a canonical service is intentionally excluded from fork configuration copying. If a library exposes shortcuts such as:

```python
mylib.start = mylib.services.Runtime.start
```

its fork integration must explicitly bind the equivalent method to the new fork's service (or provide another suitable public entry point). Calling the canonical service's bound method would act on the wrong world.

Almasi does **not** initialize a fork's application resources by default. In particular, `A.fork()` does not open an LMDB, choose a data directory, start user services, or copy persistent data. These are responsibilities of the specific library.

See [O's ontology fork architecture](https://github.com/apodgorny/o/blob/master/docs/architecture.fork.md) for an implementation with a separate `fork()` / `start()` lifecycle.

## 7. Application context is shared

Application selection is process-wide: `a.__app__` identifies the library selected through `extend()` in `__main__`. `Module.__app__` resolves that application at access time; `__lib__` separately identifies where a module class was defined.

Forking a library does **not** create another application selection. A fork can use the common application context to derive its own resources, but it must explicitly keep fork-owned state separate.

This matters for web applications and agents: a fork is a namespace/state-isolation facility, **not** an authorization or tenant-security boundary. Access policies and cross-fork references remain the application's responsibility.

## 8. Invariants and boundaries

| Property | Generic Almasi fork |
| --- | --- |
| Source files and compiled code | Shared |
| Fork-loaded Python module globals | Separate |
| Fork-loaded classes and service singletons | Separate |
| Namespace carriers and resolved-component caches | Separate |
| Ordinary public configuration | Deep-copied at fork creation |
| Canonical `import mylib` outside fork-loaded code | Unchanged |
| Process-wide `a.__app__` | Shared |
| Persistent storage and application lifecycle | Not managed |
| Repeated `fork(name)` | Error unless overridden |
| Nested forks | Supported |

**Design rule:** keep generic namespace forking in Almasi; implement any domain-specific startup, storage, and re-entry semantics in the consuming library. The O implementation is an example of that division of responsibility.

## 9. Implementation references

- `a.py` — `A.fork()`, `A.__getitem__()`, fork metadata, configuration copying, and import redirection.
- `lib/imports.py` — fork-specific module keys, separate globals, shared compiled code cache.
- `lib/service.py` — singleton lifetime per service class.
- `docs/almasi_invariants8.md` — filesystem identity, ownership, caching, and mutation invariants.

This document describes the current runtime contract, not a proposal for process isolation or automatic storage replication.
