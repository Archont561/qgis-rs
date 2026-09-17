#pragma once

#include "rust/cxx.h"
#include "qgis-sys/include/core/handle.h"

namespace qgis_shim::core {

// Note: ptr is actually a QApplication*, not ::QgsApplication*.
// We use QApplication directly to avoid including qgsapplication.h
// which triggers a static initializer crash via qgssettingsentry.h.
QGIS_DECLARE_HANDLE(QgsApplication);

} // namespace qgis_shim::core

#include "qgis-sys/src/core/application/app.rs.h"

namespace qgis_shim::core {

::std::unique_ptr<QgsApplication> application_new(
    rust::Str prefix_path) noexcept;
void application_init_qgis(QgsApplication& app) noexcept;
void application_exit_qgis(QgsApplication& app) noexcept;

} // namespace qgis_shim::core
