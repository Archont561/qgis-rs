#include <qgsconfig.h>

#include <QSysInfo>
#include <QtGlobal>

#include "qgis-sys/include/core/application_info.h"
#include "qgis-sys/include/core/convert.h"

namespace qgis_shim::core {

AppInfo application_info() noexcept {
    AppInfo out{};
    try {
        out.version = rust::String(_QGIS_VERSION);
        out.qt_version = rust::String(qVersion());
        out.platform = to_rust(QSysInfo::prettyProductName());
        return out;
    } catch (...) {
        return AppInfo{};
    }
}

}  // namespace qgis_shim::core
