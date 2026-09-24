#pragma once

#include "qgis-sys/include/core/handle.h"
#include "rust/cxx.h"

namespace qgis_shim::core {

QGIS_DECLARE_HANDLE(QgsVectorLayerHandle);

}  // namespace qgis_shim::core

#include "qgis-sys/src/core/vector_layer/layer.rs.h"

namespace qgis_shim::core {

::std::unique_ptr<QgsVectorLayerHandle> vector_layer_new(rust::Str uri, rust::Str name,
                                                         rust::Str provider) noexcept;

bool vector_layer_is_valid(const QgsVectorLayerHandle& handle) noexcept;
rust::String vector_layer_name(const QgsVectorLayerHandle& handle) noexcept;
int64_t vector_layer_feature_count(const QgsVectorLayerHandle& handle) noexcept;
rust::String vector_layer_crs_authid(const QgsVectorLayerHandle& handle) noexcept;
rust::String vector_layer_geometry_type_name(
    const QgsVectorLayerHandle& handle) noexcept;

}  // namespace qgis_shim::core
