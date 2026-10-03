#include "qgis-sys/include/native_manager/manager.h"

// The manager deliberately crosses a C ABI (malloc/free), uses Qt/QGIS
// macro-heavy headers, and owns a process-lifetime executor. The QGIS build
// provides the stronger compile/test checks for this boundary.
// NOLINTBEGIN

#include <qgsconfig.h>
#include <qgsfield.h>
#include <qgsfields.h>
#include <qgsvectorlayer.h>
#include <qgswkbtypes.h>

#include <QApplication>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonParseError>
#include <QJsonValue>
#include <QString>
#include <QSysInfo>
#include <QtGlobal>
#include <condition_variable>
#include <cstdlib>
#include <cstring>
#include <future>
#include <limits>
#include <memory>
#include <mutex>
#include <queue>
#include <string>
#include <thread>
#include <utility>
#include <vector>

#include "qgis-sys/include/core/application.h"
#include "qgis-sys/include/core/application_info.h"
#include "qgis-sys/include/core/convert.h"
#include "qgis-sys/include/core/fields.h"
#include "qgis-sys/include/core/vector_layer.h"

// Including qgsapplication.h triggers a static initializer in some QGIS
// conda-forge builds. Keep the same narrow declaration used by the legacy
// application shim while making this manager translation unit the only owner
// of QGIS operations on the C ABI path.
class QgsApplication {
   public:
    static void setPrefixPath(const QString& prefix_path, bool use_default_paths);
    static QString prefixPath();
    static void initQgis();
    static void exitQgis();
};

QGIS_DEFINE_HANDLE_DTOR(qgis_shim::core, QgsApplication, QApplication)
QGIS_DEFINE_HANDLE_DTOR(qgis_shim::core, QgsFieldsHandle, ::QgsFields)
QGIS_DEFINE_HANDLE_DTOR(qgis_shim::core, QgsVectorLayerHandle, ::QgsVectorLayer)

namespace {

QGIS_HANDLE_CAST(qgis_shim::core::QgsFieldsHandle, ::QgsFields)
QGIS_HANDLE_CAST(qgis_shim::core::QgsVectorLayerHandle, ::QgsVectorLayer)

int s_argc = 1;
char s_argv0[] = "qgis-rs";
char* s_argv[] = {s_argv0, nullptr};

}  // namespace

namespace qgis_shim::core {

::std::unique_ptr<QgsApplication> application_new(rust::Str prefix_path) noexcept {
    try {
        const QString prefix =
            QString::fromUtf8(prefix_path.data(), static_cast<int>(prefix_path.size()));
        ::QgsApplication::setPrefixPath(
            prefix.isEmpty() ? ::QgsApplication::prefixPath() : prefix, true);
        auto* app = new QApplication(s_argc, s_argv);
        return ::std::make_unique<qgis_shim::core::QgsApplication>(
            static_cast<void*>(app));
    } catch (...) {
        return nullptr;
    }
}

void application_init_qgis(QgsApplication& app) noexcept {
    try {
        if (app.ptr == nullptr) {
            return;
        }
        ::QgsApplication::initQgis();
    } catch (...) {
    }
}

void application_exit_qgis(QgsApplication& app) noexcept {
    try {
        if (app.ptr == nullptr) {
            return;
        }
        ::QgsApplication::exitQgis();
        app.ptr = nullptr;
    } catch (...) {
    }
}

AppInfo application_info() noexcept {
    AppInfo out{};
    try {
        out.version = rust::String(_QGIS_VERSION);
        out.qt_version = rust::String(qVersion());
        out.platform = to_rust(QSysInfo::prettyProductName());
    } catch (...) {
    }
    return out;
}

::std::unique_ptr<QgsVectorLayerHandle> vector_layer_new(rust::Str uri, rust::Str name,
                                                         rust::Str provider) noexcept {
    try {
        auto* layer =
            new ::QgsVectorLayer(from_rust(uri), from_rust(name), from_rust(provider));
        return ::std::make_unique<QgsVectorLayerHandle>(static_cast<void*>(layer));
    } catch (...) {
        return nullptr;
    }
}

bool vector_layer_is_valid(const QgsVectorLayerHandle& handle) noexcept {
    try {
        if (handle.ptr == nullptr) {
            return false;
        }
        return real_const(handle)->isValid();
    } catch (...) {
        return false;
    }
}

rust::String vector_layer_name(const QgsVectorLayerHandle& handle) noexcept {
    try {
        if (handle.ptr == nullptr) {
            return rust::String();
        }
        return to_rust(real_const(handle)->name());
    } catch (...) {
        return rust::String();
    }
}

int64_t vector_layer_feature_count(const QgsVectorLayerHandle& handle) noexcept {
    try {
        if (handle.ptr == nullptr) {
            return -1;
        }
        return static_cast<int64_t>(real_const(handle)->featureCount());
    } catch (...) {
        return -1;
    }
}

rust::String vector_layer_crs_authid(const QgsVectorLayerHandle& handle) noexcept {
    try {
        if (handle.ptr == nullptr) {
            return rust::String();
        }
        return to_rust(real_const(handle)->crs().authid());
    } catch (...) {
        return rust::String();
    }
}

rust::String vector_layer_geometry_type_name(
    const QgsVectorLayerHandle& handle) noexcept {
    try {
        if (handle.ptr == nullptr) {
            return rust::String();
        }
        return to_rust(::QgsWkbTypes::displayString(real_const(handle)->wkbType()));
    } catch (...) {
        return rust::String();
    }
}

::std::unique_ptr<QgsFieldsHandle> vector_layer_fields(
    const QgsVectorLayerHandle& handle) noexcept {
    try {
        if (handle.ptr == nullptr) {
            return nullptr;
        }
        auto* fields = new ::QgsFields(real_const(handle)->fields());
        return ::std::make_unique<QgsFieldsHandle>(static_cast<void*>(fields));
    } catch (...) {
        return nullptr;
    }
}

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
        if (handle.ptr == nullptr) {
            return 0;
        }
        return static_cast<int64_t>(real_const(handle)->count());
    } catch (...) {
        return 0;
    }
}

rust::String fields_name(const QgsFieldsHandle& handle, int64_t index) noexcept {
    try {
        if (handle.ptr == nullptr || index < 0 || index >= real_const(handle)->count()) {
            return rust::String();
        }
        const ::QgsField field = real_const(handle)->at(static_cast<int>(index));
        return to_rust(field.name());
    } catch (...) {
        return rust::String();
    }
}

rust::String fields_type(const QgsFieldsHandle& handle, int64_t index) noexcept {
    try {
        if (handle.ptr == nullptr || index < 0 || index >= real_const(handle)->count()) {
            return rust::String();
        }
        const ::QgsField field = real_const(handle)->at(static_cast<int>(index));
        return to_rust(field.typeName());
    } catch (...) {
        return rust::String();
    }
}

int64_t fields_precision(const QgsFieldsHandle& handle, int64_t index) noexcept {
    try {
        if (handle.ptr == nullptr || index < 0 || index >= real_const(handle)->count()) {
            return -1;
        }
        const ::QgsField field = real_const(handle)->at(static_cast<int>(index));
        return static_cast<int64_t>(field.precision());
    } catch (...) {
        return -1;
    }
}

}  // namespace qgis_shim::core

namespace {

constexpr std::uint32_t kTransportVersion = 1;

struct Request {
    explicit Request(std::string value) : json(std::move(value)) {}

    std::string json;
    std::promise<std::string> result;
};

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

bool json_id(const QJsonObject& payload, quint64* id) {
    const QJsonValue value = payload.value(QStringLiteral("layer_id"));
    if (!value.isDouble()) {
        return false;
    }

    const double number = value.toDouble();
    if (number < 1.0 ||
        number > static_cast<double>(std::numeric_limits<quint64>::max()) ||
        number != static_cast<double>(static_cast<quint64>(number))) {
        return false;
    }

    *id = static_cast<quint64>(number);
    return true;
}

class ManagerHost {
   public:
    ManagerHost() = default;

    ManagerHost(const ManagerHost&) = delete;
    ManagerHost& operator=(const ManagerHost&) = delete;

    ~ManagerHost() {
        {
            std::lock_guard lock(mutex_);
            stopping_ = true;
        }
        queue_condition_.notify_one();
        if (owner_.joinable()) {
            owner_.join();
        }
    }

    std::string submit(std::string request) {
        ensure_owner();

        if (std::this_thread::get_id() == owner_id_) {
            return dispatch(request);
        }

        auto pending = std::make_shared<Request>(std::move(request));
        std::future<std::string> result = pending->result.get_future();
        {
            std::lock_guard lock(mutex_);
            if (stopping_) {
                return compact_json(
                    failure("manager_stopped", "the native manager is stopped"));
            }
            requests_.push(std::move(pending));
        }
        queue_condition_.notify_one();
        return result.get();
    }

   private:
    void ensure_owner() {
        std::unique_lock lock(mutex_);
        if (owner_.joinable()) {
            startup_condition_.wait(lock,
                                    [this] { return owner_ready_ || owner_failed_; });
            return;
        }

        owner_ = std::thread([this] { owner_loop(); });
        startup_condition_.wait(lock, [this] { return owner_ready_ || owner_failed_; });
    }

    void owner_loop() {
        {
            std::lock_guard lock(mutex_);
            owner_id_ = std::this_thread::get_id();
            owner_ready_ = true;
        }
        startup_condition_.notify_one();

        for (;;) {
            std::shared_ptr<Request> pending;
            {
                std::unique_lock lock(mutex_);
                queue_condition_.wait(
                    lock, [this] { return stopping_ || !requests_.empty(); });
                if (requests_.empty()) {
                    if (stopping_) {
                        break;
                    }
                    continue;
                }
                pending = std::move(requests_.front());
                requests_.pop();
            }

            pending->result.set_value(dispatch(pending->json));
        }

        shutdown_qgis();
    }

    std::string dispatch(const std::string& request) noexcept {
        try {
            return dispatch_checked(request);
        } catch (const std::exception& error) {
            return compact_json(failure("internal", QString::fromUtf8(error.what())));
        } catch (...) {
            return compact_json(
                failure("internal", "the native manager caught an unknown exception"));
        }
    }

    std::string dispatch_checked(const std::string& request) {
        QJsonParseError parse_error{};
        const QJsonDocument document =
            QJsonDocument::fromJson(QByteArray::fromStdString(request), &parse_error);
        if (document.isNull() || !document.isObject()) {
            return compact_json(failure("invalid_request", parse_error.errorString()));
        }

        const QJsonObject envelope = document.object();
        const QJsonValue version = envelope.value(QStringLiteral("transport_version"));
        if (!version.isDouble()) {
            return compact_json(
                failure("invalid_request", "transport_version must be an integer"));
        }
        const int received_version = version.toInt(-1);
        if (received_version != static_cast<int>(kTransportVersion)) {
            return compact_json(failure(
                "unsupported_transport", "the native manager speaks transport version 1",
                QJsonObject{{"supported", static_cast<int>(kTransportVersion)},
                            {"received", received_version}}));
        }

        const QJsonValue operation_value = envelope.value(QStringLiteral("operation"));
        if (!operation_value.isString()) {
            return compact_json(
                failure("invalid_request", "operation must be a string"));
        }

        const QString operation = operation_value.toString();
        const QJsonValue payload_value = envelope.value(QStringLiteral("payload"));
        const QJsonObject payload =
            payload_value.isObject() ? payload_value.toObject() : QJsonObject{};

        if (operation == QStringLiteral("app_init")) {
            return compact_json(initialize());
        }
        if (!initialized_) {
            return compact_json(failure(
                "not_initialized", "app_init must succeed before a QGIS operation"));
        }
        if (operation == QStringLiteral("engine_info")) {
            return compact_json(engine_info());
        }
        if (operation == QStringLiteral("layer_new")) {
            return compact_json(layer_new(payload));
        }
        if (operation == QStringLiteral("layer_is_valid")) {
            return compact_json(layer_is_valid(payload));
        }
        if (operation == QStringLiteral("layer_name")) {
            return compact_json(layer_name(payload));
        }
        if (operation == QStringLiteral("layer_feature_count")) {
            return compact_json(layer_feature_count(payload));
        }
        if (operation == QStringLiteral("layer_crs_authid")) {
            return compact_json(layer_crs_authid(payload));
        }
        if (operation == QStringLiteral("layer_geometry_type_name")) {
            return compact_json(layer_geometry_type_name(payload));
        }
        if (operation == QStringLiteral("layer_fields")) {
            return compact_json(layer_fields(payload));
        }

        return compact_json(failure(
            "invalid_operation", "the operation is not served by the native manager"));
    }

    QJsonObject initialize() {
        if (initialized_) {
            return success(
                QJsonObject{{"initialized", true}, {"already_initialized", true}});
        }

        const QString prefix = qEnvironmentVariable("CONDA_PREFIX");
        QgsApplication::setPrefixPath(
            prefix.isEmpty() ? QgsApplication::prefixPath() : prefix, true);
        application_ = std::make_unique<QApplication>(argc_, argv_);
        QgsApplication::initQgis();
        initialized_ = true;
        return success(
            QJsonObject{{"initialized", true}, {"already_initialized", false}});
    }

    QJsonObject engine_info() const {
        QJsonArray operations;
        operations.append(QStringLiteral("app_init"));
        operations.append(QStringLiteral("engine_info"));
        operations.append(QStringLiteral("layer_new"));
        operations.append(QStringLiteral("layer_is_valid"));
        operations.append(QStringLiteral("layer_name"));
        operations.append(QStringLiteral("layer_feature_count"));
        operations.append(QStringLiteral("layer_crs_authid"));
        operations.append(QStringLiteral("layer_geometry_type_name"));
        operations.append(QStringLiteral("layer_fields"));

        return success(
            QJsonObject{{"engine", "qgis-native-manager"},
                        {"qgis_version", QStringLiteral(_QGIS_VERSION)},
                        {"qt_version", QString::fromUtf8(qVersion())},
                        {"platform", QSysInfo::prettyProductName()},
                        {"transport_version", static_cast<int>(kTransportVersion)},
                        {"initialized", initialized_},
                        {"operations", operations}});
    }

    QJsonObject layer_new(const QJsonObject& payload) {
        const QString uri = payload.value(QStringLiteral("uri")).toString();
        const QString name = payload.value(QStringLiteral("name")).toString();
        const QString provider = payload.value(QStringLiteral("provider")).toString();
        if (uri.isEmpty() || provider.isEmpty()) {
            return failure("invalid_payload", "layer_new requires uri and provider");
        }

        auto layer = std::make_unique<::QgsVectorLayer>(uri, name, provider);
        if (!layer) {
            return failure("qgis", "QgsVectorLayer returned a null object");
        }

        const quint64 id = next_id_++;
        const bool valid = layer->isValid();
        const QString display_name = layer->name();
        ::QgsVectorLayer* layer_ptr = layer.get();
        owned_layers_.push_back(std::move(layer));
        layers_.insert(id, layer_ptr);
        return success(QJsonObject{{"layer_id", static_cast<qint64>(id)},
                                   {"is_valid", valid},
                                   {"name", display_name}});
    }

    QJsonObject layer_is_valid(const QJsonObject& payload) const {
        const auto layer = lookup(payload);
        if (!layer.second) {
            return layer.first;
        }
        return success(QJsonObject{{"is_valid", layer.second->isValid()}});
    }

    QJsonObject layer_name(const QJsonObject& payload) const {
        const auto layer = lookup(payload);
        if (!layer.second) {
            return layer.first;
        }
        return success(QJsonObject{{"name", layer.second->name()}});
    }

    QJsonObject layer_feature_count(const QJsonObject& payload) const {
        const auto layer = lookup(payload);
        if (!layer.second) {
            return layer.first;
        }
        return success(QJsonObject{
            {"feature_count", static_cast<qint64>(layer.second->featureCount())}});
    }

    QJsonObject layer_crs_authid(const QJsonObject& payload) const {
        const auto layer = lookup(payload);
        if (!layer.second) {
            return layer.first;
        }
        return success(QJsonObject{{"auth_id", layer.second->crs().authid()}});
    }

    QJsonObject layer_geometry_type_name(const QJsonObject& payload) const {
        const auto layer = lookup(payload);
        if (!layer.second) {
            return layer.first;
        }
        return success(QJsonObject{
            {"name", ::QgsWkbTypes::displayString(layer.second->wkbType())}});
    }

    QJsonObject layer_fields(const QJsonObject& payload) const {
        const auto layer = lookup(payload);
        if (!layer.second) {
            return layer.first;
        }

        QJsonArray fields;
        const ::QgsFields schema = layer.second->fields();
        for (int index = 0; index < schema.count(); ++index) {
            const ::QgsField field = schema.at(index);
            fields.append(QJsonObject{{"name", field.name()},
                                      {"type", field.typeName()},
                                      {"precision", field.precision()}});
        }
        return success(QJsonObject{{"fields", fields}});
    }

    std::pair<QJsonObject, const ::QgsVectorLayer*> lookup(
        const QJsonObject& payload) const {
        quint64 id = 0;
        if (!json_id(payload, &id)) {
            return {failure("invalid_object_id", "layer_id must be a positive integer"),
                    nullptr};
        }

        const auto iterator = layers_.constFind(id);
        if (iterator == layers_.constEnd()) {
            return {failure("invalid_object_id", "the layer_id is not live"), nullptr};
        }
        return {QJsonObject{}, iterator.value()};
    }

    void shutdown_qgis() noexcept {
        try {
            layers_.clear();
            owned_layers_.clear();
            if (initialized_) {
                QgsApplication::exitQgis();
                initialized_ = false;
            }
            application_.reset();
        } catch (...) {
        }
    }

    int argc_ = 1;
    char argv_zero_[8] = "qgis-rs";
    char* argv_[2] = {argv_zero_, nullptr};
    std::mutex mutex_;
    std::condition_variable startup_condition_;
    std::condition_variable queue_condition_;
    std::queue<std::shared_ptr<Request>> requests_;
    std::thread owner_;
    std::thread::id owner_id_;
    bool owner_ready_ = false;
    bool owner_failed_ = false;
    bool stopping_ = false;
    bool initialized_ = false;
    std::unique_ptr<QApplication> application_;
    quint64 next_id_ = 1;
    // Qt 5's QHash requires copyable values, so the index stores raw pointers
    // while this adjacent owner vector keeps every live QGIS object in a
    // std::unique_ptr. The pointers never cross the C ABI or the request queue.
    QHash<quint64, ::QgsVectorLayer*> layers_;
    std::vector<std::unique_ptr<::QgsVectorLayer>> owned_layers_;
};

ManagerHost& manager() {
    // QGIS installs process-wide Qt/plugin state during initQgis(). Keeping the
    // host alive until process exit matches the existing qgis-sys lifecycle
    // helper and avoids running Qt teardown after shared-library destructors.
    // An explicit shutdown operation will own an orderly stop in a later phase.
    static ManagerHost* instance = new ManagerHost();
    return *instance;
}

char* copy_response(const std::string& response) {
    auto* buffer = static_cast<char*>(std::malloc(response.size() + 1));
    if (buffer == nullptr) {
        return nullptr;
    }
    std::memcpy(buffer, response.data(), response.size());
    buffer[response.size()] = '\0';
    return buffer;
}

}  // namespace

extern "C" char* qgis_invoke(const char* request_json) noexcept {
    try {
        const std::string request =
            request_json == nullptr ? std::string{} : request_json;
        return copy_response(manager().submit(request));
    } catch (...) {
        return copy_response(
            compact_json(failure("internal", "the native manager caught an exception")));
    }
}

extern "C" void qgis_free(char* response_json) noexcept {
    try {
        std::free(response_json);
    } catch (...) {
    }
}

extern "C" std::uint32_t qgis_transport_version() noexcept {
    try {
        return kTransportVersion;
    } catch (...) {
        return kTransportVersion;
    }
}

// NOLINTEND
