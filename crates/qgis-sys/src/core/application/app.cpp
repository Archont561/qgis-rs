#include "qgis-sys/include/core/application.h"

#include <QApplication>
#include <QString>

class QgsApplication {
  public:
    static void setPrefixPath(const QString& prefixPath,
                              bool useDefaultPaths);
    static QString prefixPath();
    static void initQgis();
    static void exitQgis();
};

QGIS_DEFINE_HANDLE_DTOR(qgis_shim::core, QgsApplication, QApplication)

namespace {

int s_argc = 1;
char s_argv0[] = "qgis-rs";
char* s_argv[] = {s_argv0, nullptr};

} // namespace

namespace qgis_shim::core {

::std::unique_ptr<QgsApplication> application_new(
    rust::Str prefix_path) noexcept {
    try {
        const QString prefix = QString::fromUtf8(
            prefix_path.data(),
            static_cast<int>(prefix_path.size()));

        ::QgsApplication::setPrefixPath(
            prefix.isEmpty() ? ::QgsApplication::prefixPath() : prefix,
            true);

        auto* app = new QApplication(s_argc, s_argv);
        return ::std::make_unique<qgis_shim::core::QgsApplication>(
            static_cast<void*>(app));
    } catch (...) {
        return nullptr;
    }
}

void application_init_qgis(QgsApplication& app) noexcept {
    try {
        QGIS_NULL_GUARD(app, );
        ::QgsApplication::initQgis();
    } catch (...) {
    }
}

void application_exit_qgis(QgsApplication& app) noexcept {
    try {
        QGIS_NULL_GUARD(app, );
        ::QgsApplication::exitQgis();
        app.ptr = nullptr;
    } catch (...) {
    }
}

} // namespace qgis_shim::core
