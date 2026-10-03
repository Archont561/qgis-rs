#include "native_manager/manager.h"

// The manager deliberately crosses a C ABI (malloc/free), uses Qt/QGIS
// macro-heavy headers, and owns a process-lifetime executor. The QGIS build
// provides the stronger compile/test checks for this boundary.
// NOLINTBEGIN

#include <qgsconfig.h>
#include <qgscoordinatereferencesystem.h>
#include <qgsfield.h>
#include <qgsfields.h>
#include <qgsfeature.h>
#include <qgsfeatureiterator.h>
#include <qgsfeaturerequest.h>
#include <qgsgeometry.h>
#include <qgsmaplayer.h>
#include <qgsmaprenderersequentialjob.h>
#include <qgsmapsettings.h>
#include <qgsproject.h>
#include <qgsrectangle.h>
#include <qgsvectorlayer.h>
#include <qgswkbtypes.h>

#include <QApplication>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonParseError>
#include <QJsonValue>
#include <QFile>
#include <QFileInfo>
#include <QImage>
#include <QList>
#include <QString>
#include <QStringList>
#include <QSysInfo>
#include <QVariant>
#include <QtGlobal>
#include <algorithm>
#include <condition_variable>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <future>
#include <limits>
#include <memory>
#include <mutex>
#include <queue>
#include <string>
#include <thread>
#include <utility>
#include <vector>

// Including qgsapplication.h triggers a static initializer in some QGIS
// conda-forge builds. Keep a narrow declaration here so this manager
// translation unit remains the only owner of QGIS operations on the C ABI path.
class QgsApplication {
   public:
    static void setPrefixPath(const QString& prefix_path, bool use_default_paths);
    static QString prefixPath();
    static void initQgis();
    static void exitQgis();
};

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
        if (operation == QStringLiteral("app_shutdown")) {
            return compact_json(shutdown());
        }
        if (!initialized_) {
            return compact_json(failure(
                "not_initialized", "app_init must succeed before a QGIS operation"));
        }
        if (operation == QStringLiteral("engine_info")) {
            return compact_json(engine_info());
        }
        if (operation == QStringLiteral("render_map")) {
            return compact_json(render_map(payload));
        }
        if (operation == QStringLiteral("export_features")) {
            return compact_json(export_features(payload));
        }
        if (operation == QStringLiteral("layer_open")) {
            return compact_json(layer_open(payload));
        }
        if (operation == QStringLiteral("layer_info")) {
            return compact_json(layer_info(payload));
        }
        if (operation == QStringLiteral("layer_close")) {
            return compact_json(layer_close(payload));
        }
        if (operation == QStringLiteral("layer_features")) {
            return compact_json(layer_features(payload));
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

    QJsonObject shutdown() {
        const quint64 released_layer_count =
            static_cast<quint64>(owned_layers_.size());
        shutdown_qgis();
        stopping_ = true;
        return success(QJsonObject{{"shutdown", true},
                                   {"released_layer_count",
                                    static_cast<qint64>(released_layer_count)}});
    }

    QJsonObject engine_info() const {
        QJsonArray operations;
        operations.append(QStringLiteral("app_init"));
        operations.append(QStringLiteral("app_shutdown"));
        operations.append(QStringLiteral("engine_info"));
        operations.append(QStringLiteral("render_map"));
        operations.append(QStringLiteral("export_features"));
        operations.append(QStringLiteral("layer_open"));
        operations.append(QStringLiteral("layer_info"));
        operations.append(QStringLiteral("layer_close"));
        operations.append(QStringLiteral("layer_features"));
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

    QJsonObject layer_open(const QJsonObject& payload) {
        return create_layer(payload, "layer_open");
    }

    QJsonObject layer_new(const QJsonObject& payload) {
        return create_layer(payload, "layer_new");
    }

    QJsonObject create_layer(const QJsonObject& payload, const char* operation) {
        const QString uri = payload.value(QStringLiteral("uri")).toString();
        const QString name = payload.value(QStringLiteral("name")).toString();
        const QString provider = payload.value(QStringLiteral("provider")).toString();
        if (uri.isEmpty() || provider.isEmpty()) {
            return failure("invalid_payload",
                           QString::fromLatin1(operation) +
                               QStringLiteral(" requires uri and provider"));
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

    QJsonObject layer_info(const QJsonObject& payload) const {
        const auto layer = lookup(payload);
        if (!layer.second) {
            return layer.first;
        }

        const ::QgsVectorLayer* vector_layer = layer.second;
        return success(QJsonObject{
            {"layer_id", static_cast<qint64>(json_layer_id(payload))},
            {"is_valid", vector_layer->isValid()},
            {"name", vector_layer->name()},
            {"feature_count", static_cast<qint64>(vector_layer->featureCount())},
            {"crs_authid", vector_layer->crs().authid()},
            {"geometry_type_name",
             ::QgsWkbTypes::displayString(vector_layer->wkbType())},
            {"fields", fields_json(vector_layer)}});
    }

    QJsonObject layer_close(const QJsonObject& payload) {
        quint64 id = 0;
        if (!json_id(payload, &id)) {
            return failure("invalid_object_id", "layer_id must be a positive integer");
        }

        const auto iterator = layers_.find(id);
        if (iterator == layers_.end()) {
            return failure("invalid_object_id", "the layer_id is not live");
        }

        ::QgsVectorLayer* layer = iterator.value();
        layers_.erase(iterator);
        const auto owner = std::find_if(
            owned_layers_.begin(), owned_layers_.end(),
            [layer](const std::unique_ptr<::QgsVectorLayer>& candidate) {
                return candidate.get() == layer;
            });
        if (owner != owned_layers_.end()) {
            owned_layers_.erase(owner);
        }
        return success(QJsonObject{{"layer_id", static_cast<qint64>(id)},
                                   {"closed", true}});
    }

    QJsonObject layer_features(const QJsonObject& payload) const {
        const auto layer = lookup(payload);
        if (!layer.second) {
            return layer.first;
        }

        quint64 offset = 0;
        if (!json_optional_integer(payload, QStringLiteral("offset"), &offset)) {
            return failure("invalid_payload", "offset must be a non-negative integer");
        }

        quint64 limit = 100;
        if (!json_optional_integer(payload, QStringLiteral("limit"), &limit) ||
            limit == 0 || limit > 1000) {
            return failure("invalid_payload", "limit must be an integer between 1 and 1000");
        }

        const ::QgsVectorLayer* vector_layer = layer.second;
        ::QgsFeatureIterator iterator = vector_layer->getFeatures();
        ::QgsFeature feature;
        quint64 skipped = 0;
        while (skipped < offset && iterator.nextFeature(feature)) {
            ++skipped;
        }

        QJsonArray features;
        while (features.size() < static_cast<int>(limit) && iterator.nextFeature(feature)) {
            QJsonObject attributes;
            const ::QgsAttributes values = feature.attributes();
            const ::QgsFields schema = vector_layer->fields();
            const int count = std::min(values.count(), schema.count());
            for (int index = 0; index < count; ++index) {
                attributes.insert(schema.at(index).name(),
                                  QJsonValue::fromVariant(values.at(index)));
            }

            features.append(QJsonObject{
                {"id", static_cast<qint64>(feature.id())},
                {"attributes", attributes},
                {"geometry_wkt", feature.geometry().asWkt()}});
        }

        const qint64 total = static_cast<qint64>(vector_layer->featureCount());
        QJsonValue next_offset = QJsonValue::Null;
        if (total >= 0 && offset + static_cast<quint64>(features.size()) <
                              static_cast<quint64>(total)) {
            next_offset = static_cast<qint64>(offset + features.size());
        }
        return success(QJsonObject{{"layer_id", static_cast<qint64>(json_layer_id(payload))},
                                   {"offset", static_cast<qint64>(offset)},
                                   {"limit", static_cast<qint64>(limit)},
                                   {"next_offset", next_offset},
                                   {"total", total},
                                   {"features", features}});
    }

    static bool parse_extent(const QString& text, ::QgsRectangle* extent) {
        const QStringList parts = text.split(',', Qt::SkipEmptyParts);
        if (parts.size() != 4) {
            return false;
        }
        bool xmin_ok = false;
        bool ymin_ok = false;
        bool xmax_ok = false;
        bool ymax_ok = false;
        const double xmin = parts.at(0).trimmed().toDouble(&xmin_ok);
        const double ymin = parts.at(1).trimmed().toDouble(&ymin_ok);
        const double xmax = parts.at(2).trimmed().toDouble(&xmax_ok);
        const double ymax = parts.at(3).trimmed().toDouble(&ymax_ok);
        if (!xmin_ok || !ymin_ok || !xmax_ok || !ymax_ok || xmin > xmax || ymin > ymax) {
            return false;
        }
        *extent = ::QgsRectangle(xmin, ymin, xmax, ymax);
        return true;
    }

    static bool parse_extent(const QJsonValue& value, ::QgsRectangle* extent) {
        if (value.isString()) {
            return parse_extent(value.toString(), extent);
        }
        if (!value.isObject()) {
            return false;
        }
        const QJsonObject object = value.toObject();
        const QStringList keys{QStringLiteral("min_x"), QStringLiteral("min_y"),
                               QStringLiteral("max_x"), QStringLiteral("max_y")};
        for (const QString& key : keys) {
            if (!object.value(key).isDouble()) {
                return false;
            }
        }
        const double xmin = object.value(keys.at(0)).toDouble();
        const double ymin = object.value(keys.at(1)).toDouble();
        const double xmax = object.value(keys.at(2)).toDouble();
        const double ymax = object.value(keys.at(3)).toDouble();
        if (xmin > xmax || ymin > ymax) {
            return false;
        }
        *extent = ::QgsRectangle(xmin, ymin, xmax, ymax);
        return true;
    }

    static QJsonObject artifact(const QString& path, const QString& format,
                                qint64 bytes) {
        return QJsonObject{{"path", path},
                           {"format", format},
                           {"bytes", bytes}};
    }

    QJsonObject render_map(const QJsonObject& payload) const {
        const QString project_path = payload.value(QStringLiteral("project")).toString();
        const QString output = payload.value(QStringLiteral("output")).toString();
        if (project_path.isEmpty() || output.isEmpty()) {
            return failure("invalid_payload", "render_map requires project and output");
        }
        const QString format = QFileInfo(output).suffix().toLower();
        if (format != QStringLiteral("png") && format != QStringLiteral("jpg") &&
            format != QStringLiteral("jpeg") && format != QStringLiteral("webp")) {
            return failure("invalid_payload",
                           "render_map supports png, jpg, jpeg, and webp output paths");
        }
        if (payload.contains(QStringLiteral("layout")) &&
            !payload.value(QStringLiteral("layout")).toString().isEmpty()) {
            return failure("qgis", "print-layout rendering is not supported by render_map");
        }

        ::QgsProject project;
        if (!project.read(project_path)) {
            return failure("qgis", "QGIS could not read the project");
        }

        QList<::QgsMapLayer*> layers;
        const QJsonArray requested_layers =
            payload.value(QStringLiteral("layers")).toArray();
        const bool restrict_layers = !requested_layers.isEmpty();
        for (auto* map_layer : project.mapLayers().values()) {
            bool selected = !restrict_layers;
            for (const QJsonValue& requested : requested_layers) {
                const QString name = requested.toString();
                selected = selected || name == map_layer->name() || name == map_layer->id();
            }
            if (selected) {
                layers.append(map_layer);
            }
        }
        if (layers.isEmpty()) {
            return failure("qgis", "the project has no selected map layers");
        }

        const int width = payload.value(QStringLiteral("width")).toInt(1024);
        const int height = payload.value(QStringLiteral("height")).toInt(768);
        const double dpi = payload.value(QStringLiteral("dpi")).toDouble(96.0);
        if (width <= 0 || height <= 0 || dpi <= 0.0) {
            return failure("invalid_payload", "render dimensions and dpi must be positive");
        }

        ::QgsMapSettings settings;
        settings.setLayers(layers);
        settings.setOutputSize(QSize(width, height));
        settings.setOutputDpi(dpi);
        if (payload.contains(QStringLiteral("crs"))) {
            ::QgsCoordinateReferenceSystem crs;
            if (!crs.createFromUserInput(payload.value(QStringLiteral("crs")).toString()) ||
                !crs.isValid()) {
                return failure("invalid_payload", "crs is not a valid QGIS coordinate reference system");
            }
            settings.setDestinationCrs(crs);
        }

        ::QgsRectangle extent;
        const QJsonValue extent_value = payload.value(QStringLiteral("extent"));
        if (!extent_value.isUndefined() && !extent_value.isNull()) {
            if (!parse_extent(extent_value, &extent)) {
                return failure("invalid_payload", "extent must be minx,miny,maxx,maxy");
            }
        } else {
            bool has_extent = false;
            for (auto* map_layer : layers) {
                const ::QgsRectangle layer_extent = map_layer->extent();
                if (!has_extent) {
                    extent = layer_extent;
                    has_extent = true;
                } else {
                    extent.combineExtentWith(layer_extent);
                }
            }
            if (!has_extent || extent.isEmpty()) {
                return failure("qgis", "the project layers have no renderable extent");
            }
        }
        settings.setExtent(extent);

        ::QgsMapRendererSequentialJob job(settings);
        job.start();
        job.waitForFinished();
        const QImage image = job.renderedImage();
        if (image.isNull() || !image.save(output)) {
            return failure("qgis", "QGIS could not write the rendered image");
        }

        const QFileInfo output_info(output);
        QJsonObject result = artifact(output, format, output_info.size());
        result.insert(QStringLiteral("width"), image.width());
        result.insert(QStringLiteral("height"), image.height());
        return success(result);
    }

    static QJsonObject feature_attributes(const ::QgsFeature& feature,
                                          const ::QgsFields& schema,
                                          const QStringList& requested_fields) {
        QJsonObject attributes;
        const ::QgsAttributes values = feature.attributes();
        for (int index = 0; index < schema.count() && index < values.count(); ++index) {
            const QString name = schema.at(index).name();
            if (!requested_fields.isEmpty() && !requested_fields.contains(name)) {
                continue;
            }
            attributes.insert(name, QJsonValue::fromVariant(values.at(index)));
        }
        return attributes;
    }

    QJsonObject export_features(const QJsonObject& payload) const {
        const QString project_path = payload.value(QStringLiteral("project")).toString();
        const QString layer_name = payload.value(QStringLiteral("layer")).toString();
        const QString output = payload.value(QStringLiteral("output")).toString();
        if (project_path.isEmpty() || layer_name.isEmpty() || output.isEmpty()) {
            return failure("invalid_payload", "export_features requires project, layer, and output");
        }
        const QString format = QFileInfo(output).suffix().toLower();
        if (format != QStringLiteral("geojson") && format != QStringLiteral("json") &&
            format != QStringLiteral("csv")) {
            return failure("invalid_payload", "export_features supports geojson and csv output paths");
        }

        ::QgsProject project;
        if (!project.read(project_path)) {
            return failure("qgis", "QGIS could not read the project");
        }
        ::QgsVectorLayer* vector_layer = nullptr;
        for (auto* map_layer : project.mapLayers().values()) {
            if (map_layer->name() == layer_name || map_layer->id() == layer_name) {
                vector_layer = qobject_cast<::QgsVectorLayer*>(map_layer);
                break;
            }
        }
        if (vector_layer == nullptr) {
            return failure("invalid_object_id", "the requested project layer is not a vector layer");
        }

        ::QgsFeatureRequest request;
        const QString filter = payload.value(QStringLiteral("filter")).toString();
        if (!filter.isEmpty()) {
            request.setFilterExpression(filter);
        }
        const QJsonValue bbox_value = payload.value(QStringLiteral("bbox"));
        if (!bbox_value.isUndefined() && !bbox_value.isNull()) {
            ::QgsRectangle rectangle;
            if (!parse_extent(bbox_value, &rectangle)) {
                return failure("invalid_payload", "bbox must be minx,miny,maxx,maxy");
            }
            request.setFilterRect(rectangle);
        }

        QStringList requested_fields;
        for (const QJsonValue& value : payload.value(QStringLiteral("fields")).toArray()) {
            const QString field = value.toString();
            if (!field.isEmpty()) {
                requested_fields.append(field);
            }
        }

        QJsonArray geojson_features;
        QString csv;
        if (format == QStringLiteral("csv")) {
            const ::QgsFields schema = vector_layer->fields();
            QStringList columns;
            for (int index = 0; index < schema.count(); ++index) {
                const QString name = schema.at(index).name();
                if (requested_fields.isEmpty() || requested_fields.contains(name)) {
                    columns.append(name);
                }
            }
            csv = columns.join(',') + QLatin1Char('\n');
        }

        quint64 feature_count = 0;
        ::QgsFeatureIterator iterator = vector_layer->getFeatures(request);
        ::QgsFeature feature;
        const ::QgsFields schema = vector_layer->fields();
        while (iterator.nextFeature(feature)) {
            const QJsonObject attributes =
                feature_attributes(feature, schema, requested_fields);
            if (format == QStringLiteral("csv")) {
                QStringList values;
                for (int index = 0; index < schema.count(); ++index) {
                    const QString column = schema.at(index).name();
                    if (!requested_fields.isEmpty() && !requested_fields.contains(column)) {
                        continue;
                    }
                    QString value = attributes.value(column).toVariant().toString();
                    value.replace(QLatin1Char('"'), QStringLiteral("\"\""));
                    if (value.contains(',') || value.contains('"') || value.contains('\n')) {
                        value.prepend(QLatin1Char('"'));
                        value.append(QLatin1Char('"'));
                    }
                    values.append(value);
                }
                csv += values.join(',') + QLatin1Char('\n');
            } else {
                const QJsonDocument geometry =
                    QJsonDocument::fromJson(feature.geometry().asJson().toUtf8());
                geojson_features.append(QJsonObject{
                    {"type", "Feature"},
                    {"id", static_cast<qint64>(feature.id())},
                    {"geometry", geometry.isObject() ? QJsonValue(geometry.object()) : QJsonValue::Null},
                    {"properties", attributes}});
            }
            ++feature_count;
        }

        QFile file(output);
        if (!file.open(QIODevice::WriteOnly | QIODevice::Truncate)) {
            return failure("io", "could not open the feature export output");
        }
        if (format == QStringLiteral("csv")) {
            file.write(csv.toUtf8());
        } else {
            const QJsonObject collection{{"type", "FeatureCollection"},
                                         {"features", geojson_features}};
            file.write(QJsonDocument(collection).toJson(QJsonDocument::Indented));
        }
        file.close();

        const QFileInfo output_info(output);
        QJsonObject result = artifact(output, format, output_info.size());
        result.insert(QStringLiteral("layer"), layer_name);
        result.insert(QStringLiteral("feature_count"), static_cast<qint64>(feature_count));
        return success(result);
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

        return success(QJsonObject{{"fields", fields_json(layer.second)}});
    }

    static quint64 json_layer_id(const QJsonObject& payload) {
        quint64 id = 0;
        json_id(payload, &id);
        return id;
    }

    static bool json_optional_integer(const QJsonObject& payload, const QString& key,
                                      quint64* value) {
        const QJsonValue candidate = payload.value(key);
        if (candidate.isUndefined() || candidate.isNull()) {
            return true;
        }
        if (!candidate.isDouble()) {
            return false;
        }
        const double number = candidate.toDouble();
        if (number < 0.0 ||
            number > static_cast<double>(std::numeric_limits<quint64>::max()) ||
            number != static_cast<double>(static_cast<quint64>(number))) {
            return false;
        }
        *value = static_cast<quint64>(number);
        return true;
    }

    static QJsonArray fields_json(const ::QgsVectorLayer* layer) {
        QJsonArray fields;
        const ::QgsFields schema = layer->fields();
        for (int index = 0; index < schema.count(); ++index) {
            const ::QgsField field = schema.at(index);
            fields.append(QJsonObject{{"name", field.name()},
                                      {"type", field.typeName()},
                                      {"precision", field.precision()}});
        }
        return fields;
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
            // QGIS owns process-wide Qt/plugin state. After exitQgis(), keep
            // the QApplication allocation leaked rather than running its
            // destructor during shared-library teardown.
            application_.release();
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
    // The explicit app_shutdown operation performs orderly owner-thread teardown.
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
