#pragma once

#include <QJsonObject>
#include <QJsonValue>
#include <QString>
#include <QtGlobal>
#include <cstdint>
#include <string>

/// The native manager's edges, with no QGIS behind them.
///
/// Everything here is a pure conversion between the three representations a
/// request passes through: the JSON envelope the protocol declares, the
/// opaque integer handle that stands in for a QGIS object, and the
/// NUL-terminated buffer that crosses the C ABI. They are separated from
/// `manager.cpp` because that translation unit cannot be loaded without a
/// QGIS prefix and a QApplication, while these functions can be — and are,
/// by `crates/qgis-sys/tests/cpp/conversions_test.cpp`.
namespace qgis_rs::native_manager {

/// The JSON transport version this manager speaks.
///
/// Mirrors `qgis_protocol::TRANSPORT_VERSION`; `qgis_transport_version()`
/// returns it without starting QGIS so a caller can refuse a mismatch before
/// paying for initialization.
constexpr std::uint32_t kTransportVersion = 1;

/// Wrap a result in the success envelope: transport version, `ok: true`.
QJsonObject success(const QJsonObject& result);

/// Wrap a failure kind and message in the error envelope.
QJsonObject failure(const char* kind, const QString& message);

/// As above, with `detail` merged beside the kind and the message.
///
/// Detail is inserted last, so a detail key named `kind` or `error`
/// deliberately overwrites the envelope's own.
QJsonObject failure(const char* kind, const QString& message, const QJsonObject& detail);

/// Print an object as the compact UTF-8 JSON that crosses the ABI.
std::string compact_json(const QJsonObject& object);

/// Read an object handle out of a JSON value.
///
/// A handle is a whole number in `[1, 2^53]`: ids start at one because zero
/// is the registry's "no such object", and the ceiling is the largest integer
/// a JSON number carries without loss, because `QJsonValue` stores every
/// number as a double. `id` is left untouched when the value is not a handle.
bool handle_from_json(const QJsonValue& value, quint64* id);

/// Read the `layer_id` handle out of a request payload.
bool json_id(const QJsonObject& payload, quint64* id);

/// Copy a response into a buffer the caller owns, NUL-terminated.
///
/// The Rust side reads it with `CStr`, so the terminator is not decoration.
/// Returns `nullptr` when the allocation fails, which `qgis_invoke` passes
/// straight through as a null response.
char* copy_response(const std::string& response);

/// Release a buffer from [`copy_response`]. Null is a no-op.
///
/// Allocation and release stay in one translation unit so the malloc/free
/// pair cannot drift apart across the ABI.
void free_response(char* response);

}  // namespace qgis_rs::native_manager
