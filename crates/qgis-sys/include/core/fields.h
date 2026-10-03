#pragma once

#include <cstdint>
#include <memory>

#include "qgis-sys/include/core/handle.h"
#include "rust/cxx.h"

namespace qgis_shim::core {

QGIS_DECLARE_HANDLE(QgsFieldsHandle);

}  // namespace qgis_shim::core

#include "qgis-sys/src/core/fields/fields.rs.h"

namespace qgis_shim::core {

::std::unique_ptr<QgsFieldsHandle> fields_new_empty() noexcept;
int64_t fields_count(const QgsFieldsHandle& handle) noexcept;
rust::String fields_name(const QgsFieldsHandle& handle, int64_t index) noexcept;
rust::String fields_type(const QgsFieldsHandle& handle, int64_t index) noexcept;
int64_t fields_precision(const QgsFieldsHandle& handle, int64_t index) noexcept;

}  // namespace qgis_shim::core
