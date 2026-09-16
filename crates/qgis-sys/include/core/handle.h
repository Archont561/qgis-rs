#pragma once

#include <cstddef>
#include <memory>

// ── Opaque handle declaration ────────────────────────────────────────────────
// Use in headers to declare a CXX-compatible opaque handle.
// The destructor is declared but NOT defined — define it in the .cpp
// where the real QGIS header is included.
//
// Usage in header:
//   namespace qgis_shim::core {
//   QGIS_DECLARE_HANDLE(QgsVectorLayerHandle);
//   }
//
// Usage in .cpp:
//   QGIS_DEFINE_HANDLE_DTOR(qgis_shim::core, QgsVectorLayerHandle, ::QgsVectorLayer)

#define QGIS_DECLARE_HANDLE(Name)                                   \
    struct Name {                                                    \
        void* ptr;                                                   \
        explicit Name(void* p) noexcept : ptr(p) {}                  \
        ~Name() noexcept;                                            \
        Name(const Name&) = delete;                                  \
        Name& operator=(const Name&) = delete;                       \
        Name(Name&&) = delete;                                       \
        Name& operator=(Name&&) = delete;                            \
    }

// ── Destructor definition ────────────────────────────────────────────────────
// Use in .cpp files where the real QGIS type is known.
//
// Usage:
//   QGIS_DEFINE_HANDLE_DTOR(qgis_shim::core, QgsVectorLayerHandle, ::QgsVectorLayer)

#define QGIS_DEFINE_HANDLE_DTOR(Namespace, Handle, RealType)        \
    Namespace::Handle::~Handle() noexcept {                          \
        delete static_cast<RealType*>(ptr);                          \
    }

// ── Safe cast helpers ────────────────────────────────────────────────────────
// Use inside anonymous namespace in .cpp files.
//
// Usage:
//   namespace {
//   QGIS_HANDLE_CAST(qgis_shim::core::QgsVectorLayerHandle, ::QgsVectorLayer)
//   }
//
// Provides:
//   real(handle)       — mutable pointer
//   real_const(handle) — const pointer

#define QGIS_HANDLE_CAST(Handle, RealType)                          \
    inline RealType* real(Handle& h) noexcept {                     \
        return static_cast<RealType*>(h.ptr);                        \
    }                                                                \
    inline const RealType* real_const(const Handle& h) noexcept {   \
        return static_cast<const RealType*>(h.ptr);                  \
    }

// ── Null-guarded getter pattern ──────────────────────────────────────────────
// Common pattern: return a default value if ptr is null.
//
// Usage:
//   QGIS_NULL_GUARD(handle, false)        — returns false if null
//   QGIS_NULL_GUARD(handle, rust::String()) — returns empty string if null
//   QGIS_NULL_GUARD(handle, -1)           — returns -1 if null

#define QGIS_NULL_GUARD(handle, default_val)                        \
    if ((handle).ptr == nullptr) {                                   \
        return (default_val);                                        \
    }
