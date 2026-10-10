#include "native_manager/conversions.h"

#include <QByteArray>
#include <QJsonDocument>
#include <QLatin1String>
#include <cstdlib>
#include <cstring>

namespace qgis_sys::native_manager {

QJsonObject success(const QJsonObject& result) {
    return QJsonObject{{"transport_version", static_cast<int>(kTransportVersion)},
                       {"ok", true},
                       {"result", result}};
}

QJsonObject failure(const char* kind, const QString& message) {
    return QJsonObject{{"transport_version", static_cast<int>(kTransportVersion)},
                       {"ok", false},
                       {"result", QJsonObject{{"kind", kind}, {"error", message}}}};
}

QJsonObject failure(const char* kind, const QString& message,
                    const QJsonObject& detail) {
    QJsonObject result{{"kind", kind}, {"error", message}};
    for (auto it = detail.constBegin(); it != detail.constEnd(); ++it) {
        result.insert(it.key(), it.value());
    }
    return QJsonObject{{"transport_version", static_cast<int>(kTransportVersion)},
                       {"ok", false},
                       {"result", result}};
}

std::string compact_json(const QJsonObject& object) {
    return QJsonDocument(object).toJson(QJsonDocument::Compact).toStdString();
}

namespace {

// The largest integer a JSON number carries without loss: QJsonValue stores
// every number as a double, so anything above 2^53 may already have been
// rounded to a different whole number by the parser.
constexpr double kMaxExactHandle = static_cast<double>(1ULL << 53U);

}  // namespace

bool handle_from_json(const QJsonValue& value, quint64* id) {
    if (!value.isDouble()) {
        return false;
    }

    const double number = value.toDouble();
    if (number < 1.0 || number > kMaxExactHandle ||
        number != static_cast<double>(static_cast<quint64>(number))) {
        return false;
    }

    *id = static_cast<quint64>(number);
    return true;
}

bool json_id(const QJsonObject& payload, quint64* id) {
    // QLatin1String rather than QStringLiteral: the macro expands to an
    // unnamed enum that three clang-tidy checks then report against this
    // line, and the key is ASCII anyway.
    return handle_from_json(payload.value(QLatin1String("layer_id")), id);
}

// malloc and free, deliberately: this pair *is* the C ABI. The buffer is
// allocated here and released by qgis_free on the other side of a boundary
// no smart pointer crosses, which is the whole reason both halves live in
// this one translation unit.
char* copy_response(const std::string& response) {
    // NOLINTNEXTLINE(cppcoreguidelines-no-malloc)
    auto* buffer = static_cast<char*>(std::malloc(response.size() + 1));
    if (buffer == nullptr) {
        return nullptr;
    }
    std::memcpy(buffer, response.data(), response.size());
    buffer[response.size()] = '\0';
    return buffer;
}

// NOLINTNEXTLINE(cppcoreguidelines-no-malloc)
void free_response(char* response) { std::free(response); }

}  // namespace qgis_sys::native_manager
