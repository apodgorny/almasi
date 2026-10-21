# Almasi Invariants 8 — File identity and directory operations

This is the current filesystem contract. It supplements invariants 1–7 and supersedes their ordinary carrier metadata names and earlier write/cache descriptions. Historical notes remain historical.

## Identity and ownership

Every `File` or `Directory` has three canonical coordinates: `__lib__`, `__path__`, and `__route__`. Only `File` accesses their storage directly. All callers, including `Directory`, use public methods:

```python
item.get_lib()
item.get_path()
item.get_route()
item.get_name()
item.is_directory()
item.load()
```

`get_path()` returns the canonical physical path; `get_route()` returns the logical namespace route; `get_name()` derives the physical basename. `Directory` inherits the identity getters and overrides `is_directory()` to return `True`. `File.is_directory()` returns `False`.

There are no `.lib`, `.path`, `.route`, `.name`, `.data`, `.hash`, `.load_method`, or `.hash_method` compatibility properties. Those ordinary names can resolve filesystem children. Methods remain reserved: `get_lib`, `get_path`, `get_route`, `get_name`, `is_directory`, `load`, `join`, `mkdir`, `read`, `write`, `copy`, and `link`. Explicit `read('is_directory.md')` can read a resource whose stem coincides with a method.

Library class metadata, Python module special attributes, plugin ownership, and domain fields are separate contracts. For example, `A.__path__`, `module.__file__`, `Plugin.lib`, and `Container.path` are not carrier property aliases.

## Directory operations

| Signature | Contract |
|---|---|
| `join(*parts)` | Return an absolute validated path without creating anything; zero arguments return the directory path |
| `mkdir(*parts)` | Create nested directories and return a natively resolved `Directory` |
| `read(name)` | Load an explicit filename through the responsible existing plugin |
| `write(name, value)` | Serialize through a plugin and atomically replace the destination |
| `copy(name, source)` | Copy a regular file byte-for-byte and atomically replace the destination |
| `link(name, path)` | Create or retarget an explicit filesystem link |

Root library faces delegate these six operations to their root `Directory`.

```python
output = mylib.mkdir('assets', 'video')
output.write('notes.md', '# Welcome')
output.write('scenario.json', {'scenes': []})
output.copy('narration.wav', source_filename)

notes    = output.read('notes.md')
scenario = output.scenario
cover    = output.join('images', 'cover.png')
```

`join()` accepts relative string components, rejects absolute components, parent traversal outside the base, and symlink escapes. Its result need not exist. `mkdir()` also rejects empty, dot, parent, and symlink components; lookup itself never creates directories.

`read`, `write`, and `copy` accept one basename, reject traversal and symbolic-link destinations, and propagate exceptions. Reads select the exact filename, independently of the normal stem-based extension priority. Text plugins support UTF-8 `.txt` and `.md`; JSON supports ordinary JSON values, including `null`. Plugin and library lineage priority remain unchanged. Unknown formats cannot be read or written through plugins; `copy` supports arbitrary binary data and unknown extensions without plugins.

`copy` requires an existing regular readable source. It does not recursively copy directories. Copying onto the same file raises `ValueError`, including hard-link identity. Explicit `link()` remains the operation for intentional mounts outside the library tree.

## Atomic publication

`write` and `copy` create a unique hidden temporary file in the destination directory, preserve the destination extension, finish serialization or byte copying, then call `os.replace`. Temporary files are excluded from normal discovery. A failure before replacement preserves the old destination and its caches; temporary files are removed and the original exception propagates. A cleanup failure is attached to the original exception rather than replacing it.

These methods provide atomic replacement on the filesystem. They do not synchronize files or directory metadata and do not promise power-loss durability. Copying preserves bytes, not source permissions or timestamps. Streaming and externally managed writes retain their existing protocols.

## Memoization and mutation

The namespace face owns `__children__` carriers. `File` owns `_data`, `_hash`, `_load_method`, `_hash_method`, and its loaded state. Legitimate `None` is memoized. Normal reads do not probe timestamps or hashes on every access.

Successful mutations invalidate related bindings and reset affected retained file carriers in the receiving face. Unrelated cached resources remain intact. A root `Directory` representing the owning library root shares that library's existing child cache. Creating a local override preserves local-first resolution and existing plugin priority. Retargeting a link removes its old namespace binding.

Previously returned values remain snapshots. Independently constructed directory faces, inherited consumer faces already holding a cached resource, and external filesystem edits have no automatic global invalidation. There is no new global registry or freshness policy. Callers that need one coherent mutation/read lifetime should retain and use the same namespace face.

Python module identity remains authoritative in `sys.modules`; service identity remains owned by the service class. Replacing a Python source file does not introduce module reload semantics. The root `test.py` runner is excluded from component discovery across inherited library roots.

## Explicit source ownership

The resolver passes the library whose filesystem layer supplied the component as
`source_lib`, through the existing plugin call:

```python
plugin(name, parent_path, parent_route, source_lib=source_lib)
```

`Plugin.lib` remains the owner of the loader plugin. It is separate from
`source_lib`: an inherited loader can load a file supplied by another library.
File carriers and newly loaded Python modules retain the supplied source library.
An inherited component keeps its defining layer; a local override belongs to its
local layer. Plugin priority and namespace traversal remain unchanged.

`Imports.load_module(lib, ...)` uses its explicit `lib` argument. The shared
`Imports.__lib__` value does not determine module ownership. Cached modules in
`sys.modules` are reused without rebinding their owner or changing class/service
identity. This refines the older three-argument plugin call shape in invariants 5;
custom loader plugins must accept and forward the explicit `source_lib` argument.
