#pragma once

#include <QByteArray>
#include <QString>

#include "rust/cxx.h"

namespace qgis_shim::core {

inline rust::String to_rust(const QString& s) noexcept {
    const QByteArray ba = s.toUtf8();
    return rust::String(ba.constData(), static_cast<std::size_t>(ba.size()));
}

inline QString from_rust(rust::Str s) noexcept {
    return QString::fromUtf8(s.data(), static_cast<int>(s.size()));
}

}  // namespace qgis_shim::core
