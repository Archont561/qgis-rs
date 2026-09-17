#include "qgis-sys/include/core/vector_layer.h"
#include "qgis-sys/include/core/convert.h"

#include <qgsvectorlayer.h>

QGIS_DEFINE_HANDLE_DTOR(qgis_shim::core, QgsVectorLayerHandle, ::QgsVectorLayer)

namespace {

QGIS_HANDLE_CAST(qgis_shim::core::QgsVectorLayerHandle, ::QgsVectorLayer)

} // namespace

namespace qgis_shim::core {

::std::unique_ptr<QgsVectorLayerHandle> vector_layer_new(
    rust::Str uri,
    rust::Str name,
    rust::Str provider) noexcept {
    try {
        auto* layer = new ::QgsVectorLayer(
            from_rust(uri), from_rust(name), from_rust(provider));
        return ::std::make_unique<QgsVectorLayerHandle>(
            static_cast<void*>(layer));
    } catch (...) {
        return nullptr;
    }
}

bool vector_layer_is_valid(
    const QgsVectorLayerHandle& handle) noexcept {
    try {
        QGIS_NULL_GUARD(handle, false);
        return real_const(handle)->isValid();
    } catch (...) {
        return false;
    }
}

rust::String vector_layer_name(
    const QgsVectorLayerHandle& handle) noexcept {
    try {
        QGIS_NULL_GUARD(handle, rust::String());
        return to_rust(real_const(handle)->name());
    } catch (...) {
        return rust::String();
    }
}

int64_t vector_layer_feature_count(
    const QgsVectorLayerHandle& handle) noexcept {
    try {
        QGIS_NULL_GUARD(handle, -1);
        return static_cast<int64_t>(real_const(handle)->featureCount());
    } catch (...) {
        return -1;
    }
}

rust::String vector_layer_crs_authid(
    const QgsVectorLayerHandle& handle) noexcept {
    try {
        QGIS_NULL_GUARD(handle, rust::String());
        return to_rust(real_const(handle)->crs().authid());
    } catch (...) {
        return rust::String();
    }
}

rust::String vector_layer_geometry_type_name(
    const QgsVectorLayerHandle& handle) noexcept {
    try {
        QGIS_NULL_GUARD(handle, rust::String());
        return to_rust(
            ::QgsWkbTypes::displayString(real_const(handle)->wkbType()));
    } catch (...) {
        return rust::String();
    }
}

} // namespace qgis_shim::core
