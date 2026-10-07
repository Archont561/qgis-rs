// The native manager's own tests, for the part of it that is not QGIS.
//
// `manager.cpp` cannot be unit-tested as a whole: it owns a process-lifetime
// QApplication and a QGIS prefix, and starting those is what the Rust
// integration tests under `crates/qgis-sys/tests/*.rs` already do. What *can*
// be tested in isolation is the manager's edges — the JSON envelope every
// answer is wrapped in, the handle encoding that carries a layer id across
// that envelope, and the malloc/free pair that carries a response across the
// C ABI. Those are pure functions over Qt and the standard library, they are
// where an off-by-one costs a leak or a wrong layer, and they live in
// `conversions.cpp` precisely so this file can reach them.
//
// Examples pin the shapes a reader needs to see; RapidCheck properties pin the
// invariants over all inputs (D11: tests live in tests/, never in src/).

#include "native_manager/conversions.h"

#include <gtest/gtest.h>
#include <rapidcheck.h>
#include <rapidcheck/gtest.h>

#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonParseError>
#include <QJsonValue>
#include <QString>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <map>
#include <string>

namespace {

using qgis_rs::native_manager::compact_json;
using qgis_rs::native_manager::copy_response;
using qgis_rs::native_manager::failure;
using qgis_rs::native_manager::free_response;
using qgis_rs::native_manager::handle_from_json;
using qgis_rs::native_manager::json_id;
using qgis_rs::native_manager::kTransportVersion;
using qgis_rs::native_manager::success;

/// The largest integer a JSON number carries without loss. QJsonValue stores
/// every number as a double, so this is the real ceiling of a handle, not
/// `UINT64_MAX`.
constexpr std::uint64_t kMaxExactJsonInteger = 1ULL << 53U;

/// Parse a compact JSON document back into the object it was printed from.
QJsonObject reparse(const std::string& json) {
    return QJsonDocument::fromJson(QByteArray::fromStdString(json)).object();
}

/// Read the shared Rust/Python/TypeScript/C++ lifecycle contract.
QJsonObject shared_lifecycle_fixture() {
    QFile file(QString::fromUtf8(QGIS_LAYER_LIFECYCLE_FIXTURE_PATH));
    EXPECT_TRUE(file.open(QIODevice::ReadOnly)) << file.errorString().toStdString();
    if (!file.isOpen()) {
        return {};
    }

    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(file.readAll(), &error);
    EXPECT_EQ(error.error, QJsonParseError::NoError)
        << error.errorString().toStdString();
    EXPECT_TRUE(document.isObject());
    return document.object();
}

/// A QJsonObject of string values, from a generated map. Enough shape to prove
/// the envelope carries a payload through untouched.
QJsonObject object_of(const std::map<std::string, std::string>& entries) {
    QJsonObject object;
    for (const auto& entry : entries) {
        object.insert(QString::fromStdString(entry.first),
                      QString::fromStdString(entry.second));
    }
    return object;
}

/// Generated text, restricted to printable ASCII.
///
/// Not timidity: the wire is UTF-8 by contract, and `QString::fromStdString`
/// decodes it as such. An arbitrary byte string is therefore not a smaller
/// version of the same input — it is a *different* input, one that Qt
/// replaces rather than carries, and two distinct invalid sequences collapse
/// onto the same replacement character. Properties about what the envelope
/// preserves are stated over text it can preserve; what happens to the rest
/// is pinned by example in `FailureReplacesTextThatIsNotUtf8` below.
rc::Gen<std::string> text() {
    return rc::gen::container<std::string>(rc::gen::inRange<char>(' ', '\x7f'));
}

/// Generated string-to-string payloads, over that same alphabet.
rc::Gen<std::map<std::string, std::string>> text_map() {
    return rc::gen::container<std::map<std::string, std::string>>(text(), text());
}

// ── the envelope ─────────────────────────────────────────────────────────────

TEST(Envelope, SuccessCarriesTheTransportVersionAndTheResult) {
    const QJsonObject envelope = success(QJsonObject{{"initialized", true}});

    EXPECT_EQ(envelope.value("transport_version").toInt(),
              static_cast<int>(kTransportVersion));
    EXPECT_TRUE(envelope.value("ok").toBool());
    EXPECT_TRUE(envelope.value("result").toObject().value("initialized").toBool());
}

TEST(Envelope, FailureNamesAKindAndAMessage) {
    const QJsonObject envelope =
        failure("invalid_request", "operation must be a string");

    EXPECT_FALSE(envelope.value("ok").toBool());
    const QJsonObject result = envelope.value("result").toObject();
    EXPECT_EQ(result.value("kind").toString(), QStringLiteral("invalid_request"));
    EXPECT_EQ(result.value("error").toString(),
              QStringLiteral("operation must be a string"));
}

TEST(Envelope, FailureDetailIsMergedBesideTheKindAndMessage) {
    const QJsonObject envelope =
        failure("unsupported_transport", "the native manager speaks transport version 1",
                QJsonObject{{"supported", 1}, {"received", 7}});

    const QJsonObject result = envelope.value("result").toObject();
    EXPECT_EQ(result.value("kind").toString(), QStringLiteral("unsupported_transport"));
    EXPECT_EQ(result.value("supported").toInt(), 1);
    EXPECT_EQ(result.value("received").toInt(), 7);
}

/// What the envelope does with bytes that are not UTF-8, found by the
/// property above before it was constrained: Qt decodes every string as UTF-8
/// and substitutes U+FFFD for what it cannot decode. The manager never
/// produces such a message itself — the kinds are literals and the messages
/// come from Qt — but a layer name read off a corrupt file could, and the
/// answer is a replacement character rather than a crash or a truncation.
TEST(Envelope, FailureReplacesTextThatIsNotUtf8) {
    const std::string invalid = "\xed";

    const QJsonObject envelope = failure("internal", QString::fromStdString(invalid));

    EXPECT_EQ(envelope.value("result").toObject().value("error").toString(),
              QString(QChar(0xFFFD)));
}

TEST(Envelope, SharedLifecycleSuccessFixturesMatchTheTransportContract) {
    const QJsonObject fixture = shared_lifecycle_fixture();
    const QJsonObject operations = fixture.value("operations").toObject();
    ASSERT_EQ(operations.size(), 4);

    for (auto it = operations.constBegin(); it != operations.constEnd(); ++it) {
        const QJsonObject test_case = it.value().toObject();
        const QJsonObject request = test_case.value("request").toObject();
        EXPECT_EQ(request.value("transport_version").toInt(),
                  static_cast<int>(kTransportVersion));
        EXPECT_EQ(request.value("operation").toString().toStdString(),
                  it.key().toStdString());

        const QJsonObject expected = test_case.value("response").toObject();
        ASSERT_TRUE(expected.value("ok").toBool());
        const QJsonObject actual =
            reparse(compact_json(success(expected.value("result").toObject())));
        EXPECT_EQ(compact_json(actual), compact_json(expected))
            << it.key().toStdString();
    }
}

TEST(Envelope, SharedLifecycleErrorFixturesMatchExactErrorEnvelopes) {
    const QJsonObject fixture = shared_lifecycle_fixture();
    const QJsonObject errors = fixture.value("errors").toObject();
    ASSERT_EQ(errors.size(), 2);

    for (auto it = errors.constBegin(); it != errors.constEnd(); ++it) {
        const QJsonObject test_case = it.value().toObject();
        const QJsonObject request = test_case.value("request").toObject();
        EXPECT_EQ(request.value("transport_version").toInt(),
                  static_cast<int>(kTransportVersion));
        EXPECT_EQ(request.value("operation").toString().toStdString(), "layer_info");

        const QJsonObject expected = test_case.value("response").toObject();
        const QJsonObject result = expected.value("result").toObject();
        QJsonObject detail = result;
        detail.remove("kind");
        detail.remove("error");
        const std::string kind = result.value("kind").toString().toStdString();
        const QJsonObject actual = reparse(compact_json(
            failure(kind.c_str(), result.value("error").toString(), detail)));
        EXPECT_EQ(compact_json(actual), compact_json(expected))
            << it.key().toStdString();
    }
}

/// Whatever the payload, the envelope around it is the one the protocol
/// declares: a transport version, an `ok` flag, and the result unchanged.
RC_GTEST_PROP(Envelope, SuccessRoundTripsItsResultThroughCompactJson, ()) {
    const QJsonObject result = object_of(*text_map());

    const QJsonObject envelope = reparse(compact_json(success(result)));

    RC_ASSERT(envelope.value("transport_version").toInt() ==
              static_cast<int>(kTransportVersion));
    RC_ASSERT(envelope.value("ok").toBool());
    RC_ASSERT(envelope.value("result").toObject() == result);
}

/// A failure answers with `ok: false` and never loses the kind or the message,
/// however much detail is merged beside them.
RC_GTEST_PROP(Envelope, FailureKeepsItsKindAndMessageBesideAnyDetail, ()) {
    const auto kind = *text();
    const auto message = *text();
    std::map<std::string, std::string> payload = *text_map();
    // `kind` and `error` are the envelope's own keys; detail is merged after
    // them, so a collision is an overwrite the manager intends.
    payload.erase("kind");
    payload.erase("error");

    const QJsonObject envelope = reparse(compact_json(
        failure(kind.c_str(), QString::fromStdString(message), object_of(payload))));

    RC_ASSERT(!envelope.value("ok").toBool());
    const QJsonObject result = envelope.value("result").toObject();
    RC_ASSERT(result.value("kind").toString().toStdString() == kind);
    RC_ASSERT(result.value("error").toString().toStdString() == message);
    for (const auto& entry : payload) {
        RC_ASSERT(
            result.value(QString::fromStdString(entry.first)).toString().toStdString() ==
            entry.second);
    }
}

// ── handle conversions ───────────────────────────────────────────────────────

TEST(Handle, ReadsTheLayerIdOutOfAPayload) {
    quint64 id = 0;

    EXPECT_TRUE(json_id(QJsonObject{{"layer_id", 42}}, &id));
    EXPECT_EQ(id, 42U);
}

TEST(Handle, RejectsAPayloadWithoutALayerId) {
    quint64 id = 7;

    EXPECT_FALSE(json_id(QJsonObject{{"name", "points"}}, &id));
    EXPECT_EQ(id, 7U) << "a rejected handle must not be written";
}

TEST(Handle, RejectsEverythingThatIsNotAPositiveWholeNumber) {
    quint64 id = 0;

    EXPECT_FALSE(handle_from_json(QJsonValue(0), &id)) << "ids start at 1";
    EXPECT_FALSE(handle_from_json(QJsonValue(-1), &id));
    EXPECT_FALSE(handle_from_json(QJsonValue(1.5), &id));
    EXPECT_FALSE(handle_from_json(QJsonValue(QStringLiteral("3")), &id))
        << "a string is not a handle, even when it reads like one";
    EXPECT_FALSE(handle_from_json(QJsonValue(), &id));
    EXPECT_FALSE(handle_from_json(
        QJsonValue(static_cast<double>(std::numeric_limits<quint64>::max()) * 2.0),
        &id));
}

/// Every id the manager can hand out survives the round trip through a JSON
/// number. The ceiling is the double mantissa, which is why the registry's
/// ids are checked against it rather than against `UINT64_MAX`.
RC_GTEST_PROP(Handle, EveryRepresentableIdRoundTrips, ()) {
    const auto original = *rc::gen::inRange<std::uint64_t>(1, kMaxExactJsonInteger + 1);

    quint64 parsed = 0;
    RC_ASSERT(
        json_id(QJsonObject{{"layer_id", static_cast<double>(original)}}, &parsed));
    RC_ASSERT(parsed == original);
}

/// A fractional number is never a handle, whatever its magnitude.
RC_GTEST_PROP(Handle, RejectsFractionalIds, ()) {
    const auto whole = *rc::gen::inRange<std::uint64_t>(1, 1ULL << 40U);
    const auto fraction = *rc::gen::inRange(1, 999);
    const double number =
        static_cast<double>(whole) + (static_cast<double>(fraction) / 1000.0);

    quint64 parsed = 0;
    RC_ASSERT(!handle_from_json(QJsonValue(number), &parsed));
}

// ── the string that crosses the C ABI ────────────────────────────────────────

TEST(Response, IsNulTerminatedAndIndependentOfItsSource) {
    std::string source = R"({"ok":true})";

    char* copy = copy_response(source);
    ASSERT_NE(copy, nullptr);
    source.clear();

    EXPECT_STREQ(copy, R"({"ok":true})");
    free_response(copy);
}

TEST(Response, FreeingNothingIsSafe) {
    free_response(nullptr);  // mirrors qgis_free on a null response
}

/// Every byte crosses, and one NUL is appended: the Rust side reads the buffer
/// with `CStr`, so a missing terminator is an out-of-bounds read and a short
/// copy is a truncated answer.
RC_GTEST_PROP(Response, CopiesEveryByteAndTerminates, (const std::string& response)) {
    char* copy = copy_response(response);
    RC_ASSERT(copy != nullptr);

    const bool identical = std::memcmp(copy, response.data(), response.size()) == 0;
    const bool terminated = copy[response.size()] == '\0';
    free_response(copy);

    RC_ASSERT(identical);
    RC_ASSERT(terminated);
}

}  // namespace
