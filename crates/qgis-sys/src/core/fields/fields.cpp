#include "qgis-sys/include/core/fields.h"

#include <qgsfield.h>
#include <qgsfields.h>

#include "qgis-sys/include/core/convert.h"

QGIS_DEFINE_HANDLE_DTOR(qgis_shim::core, QgsFieldsHandle, ::QgsFields)

namespace {

QGIS_HANDLE_CAST(qgis_shim::core::QgsFieldsHandle, ::QgsFields)

bool valid_field_index(const qgis_shim::core::QgsFieldsHandle& handle,
                       int64_t index) noexcept {
    return handle.ptr != nullptr && index >= 0 && index < real_const(handle)->count();
}

}  // namespace

namespace qgis_shim::core {

::std::unique_ptr<QgsFieldsHandle> fields_new_empty() noexcept {
    try {
        return ::std::make_unique<QgsFieldsHandle>(
            static_cast<void*>(new ::QgsFields()));
    } catch (...) {
        return nullptr;
    }
}

int64_t fields_count(const QgsFieldsHandle& handle) noexcept {
    try {
        QGIS_NULL_GUARD(handle, 0);
        return static_cast<int64_t>(real_const(handle)->count());
    } catch (...) {
        return 0;
    }
}

rust::String fields_name(const QgsFieldsHandle& handle, int64_t index) noexcept {
    try {
        if (!valid_field_index(handle, index)) {
            return rust::String();
        }
        const auto field = real_const(handle)->at(static_cast<int>(index));
        return to_rust(field.name());
    } catch (...) {
        return rust::String();
    }
}

rust::String fields_type(const QgsFieldsHandle& handle, int64_t index) noexcept {
    try {
        if (!valid_field_index(handle, index)) {
            return rust::String();
        }
        const auto field = real_const(handle)->at(static_cast<int>(index));
        return to_rust(field.typeName());
    } catch (...) {
        return rust::String();
    }
}

int64_t fields_precision(const QgsFieldsHandle& handle, int64_t index) noexcept {
    try {
        if (!valid_field_index(handle, index)) {
            return -1;
        }
        const auto field = real_const(handle)->at(static_cast<int>(index));
        return static_cast<int64_t>(field.precision());
    } catch (...) {
        return -1;
    }
}

}  // namespace qgis_shim::core
