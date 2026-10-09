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

/// The shared Rust/Python/TypeScript/C++ lifecycle contract, or an empty object
/// when the file cannot be read or is not a JSON object. Each caller asserts
/// the result is non-empty, so a missing fixture fails the test rather than
/// passing it vacuously.
QJsonObject shared_lifecycle_fixture() {
    QFile file(QString::fromUtf8(QGIS_LAYER_LIFECYCLE_FIXTURE_PATH));
    if (!file.open(QIODevice::ReadOnly)) {
        return {};
    }
    return QJsonDocument::fromJson(file.readAll()).object();
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
    // Given a result the manager has computed
    const QJsonObject result{{"initialized", true}};

    // When the result is wrapped in the success envelope
    const QJsonObject envelope = success(result);

    // Then the envelope declares the transport version and ok, and carries the result
    EXPECT_EQ(envelope.value("transport_version").toInt(),
              static_cast<int>(kTransportVersion));
    EXPECT_TRUE(envelope.value("ok").toBool());
    EXPECT_TRUE(envelope.value("result").toObject().value("initialized").toBool());
}

TEST(Envelope, FailureNamesAKindAndCarriesItsMessage) {
    // Given a failure kind and the message that describes it
    const QString message = QStringLiteral("message-1");

    // When the failure is wrapped in the error envelope
    const QJsonObject envelope = failure("invalid_request", message);

    // Then ok is false, and the result names the kind and carries the message verbatim
    EXPECT_FALSE(envelope.value("ok").toBool());
    const QJsonObject result = envelope.value("result").toObject();
    EXPECT_EQ(result.value("kind").toString(), QStringLiteral("invalid_request"));
    EXPECT_EQ(result.value("error").toString(), message);
}

TEST(Envelope, FailureDetailIsMergedBesideTheKindAndMessage) {
    // Given structured detail that explains a failure
    const QJsonObject detail{{"supported", 1}, {"received", 7}};

    // When the failure is wrapped with that detail
    const QJsonObject envelope = failure("unsupported_transport", "message-2", detail);

    // Then the detail sits beside the kind in the result
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
    // Given a message containing a byte that is not valid UTF-8
    const std::string invalid = "\xed";

    // When the failure is wrapped in the envelope
    const QJsonObject envelope = failure("internal", QString::fromStdString(invalid));

    // Then the byte is replaced by U+FFFD rather than crashing or truncating the text
    EXPECT_EQ(envelope.value("result").toObject().value("error").toString(),
              QString(QChar(0xFFFD)));
}

TEST(Envelope, SharedLifecycleSuccessFixturesMatchTheTransportContract) {
    // Given the shared lifecycle fixture and its four success cases
    const QJsonObject fixture = shared_lifecycle_fixture();
    ASSERT_FALSE(fixture.isEmpty()) << "layer-lifecycle.json must load and parse";
    const QJsonObject operations = fixture.value("operations").toObject();
    ASSERT_EQ(operations.size(), 4);

    for (auto it = operations.constBegin(); it != operations.constEnd(); ++it) {
        const QJsonObject test_case = it.value().toObject();
        const QJsonObject request = test_case.value("request").toObject();
        const QJsonObject expected = test_case.value("response").toObject();
        ASSERT_TRUE(expected.value("ok").toBool()) << it.key().toStdString();

        // When the expected result is rebuilt through the success envelope
        const QJsonObject actual =
            reparse(compact_json(success(expected.value("result").toObject())));

        // Then the request names the operation and the envelope matches the fixture
        EXPECT_EQ(request.value("transport_version").toInt(),
                  static_cast<int>(kTransportVersion));
        EXPECT_EQ(request.value("operation").toString().toStdString(),
                  it.key().toStdString());
        EXPECT_EQ(compact_json(actual), compact_json(expected))
            << it.key().toStdString();
    }
}

TEST(Envelope, SharedLifecycleErrorFixturesMatchExactErrorEnvelopes) {
    // Given the shared lifecycle fixture and its two error cases
    const QJsonObject fixture = shared_lifecycle_fixture();
    ASSERT_FALSE(fixture.isEmpty()) << "layer-lifecycle.json must load and parse";
    const QJsonObject errors = fixture.value("errors").toObject();
    ASSERT_EQ(errors.size(), 2);

    for (auto it = errors.constBegin(); it != errors.constEnd(); ++it) {
        const QJsonObject test_case = it.value().toObject();
        const QJsonObject request = test_case.value("request").toObject();
        const QJsonObject expected = test_case.value("response").toObject();
        const QJsonObject result = expected.value("result").toObject();

        // When the kind, message and detail are rebuilt through the failure envelope
        QJsonObject detail = result;
        detail.remove("kind");
        detail.remove("error");
        const std::string kind = result.value("kind").toString().toStdString();
        const QJsonObject actual = reparse(compact_json(
            failure(kind.c_str(), result.value("error").toString(), detail)));

        // Then the request is a layer_info call and the envelope matches the fixture
        // exactly
        EXPECT_EQ(request.value("transport_version").toInt(),
                  static_cast<int>(kTransportVersion));
        EXPECT_EQ(request.value("operation").toString().toStdString(), "layer_info");
        EXPECT_EQ(compact_json(actual), compact_json(expected))
            << it.key().toStdString();
    }
}

/// Given any payload, the success envelope carries the protocol's transport
/// version and an `ok` flag, and the result survives unchanged.
RC_GTEST_PROP(Envelope, SuccessRoundTripsItsResultThroughCompactJson, ()) {
    // Given a generated payload
    const QJsonObject result = object_of(*text_map());

    // When it is wrapped, printed compactly and parsed back
    const QJsonObject envelope = reparse(compact_json(success(result)));

    // Then the envelope is the declared success shape around the same result
    RC_ASSERT(envelope.value("transport_version").toInt() ==
              static_cast<int>(kTransportVersion));
    RC_ASSERT(envelope.value("ok").toBool());
    RC_ASSERT(envelope.value("result").toObject() == result);
}

/// A failure answers with `ok: false` and never loses the kind or the message,
/// however much detail is merged beside them.
RC_GTEST_PROP(Envelope, FailureKeepsItsKindAndMessageBesideAnyDetail, ()) {
    // Given a generated kind, message and detail payload
    const auto kind = *text();
    const auto message = *text();
    std::map<std::string, std::string> payload = *text_map();
    // `kind` and `error` are the envelope's own keys; detail is merged after
    // them, so a collision is an overwrite the manager intends.
    payload.erase("kind");
    payload.erase("error");

    // When the failure is wrapped with that detail and parsed back
    const QJsonObject envelope = reparse(compact_json(
        failure(kind.c_str(), QString::fromStdString(message), object_of(payload))));

    // Then ok is false, the kind and message are intact, and every detail entry survives
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
    // Given a request payload that names a layer by id
    const QJsonObject payload{{"layer_id", 42}};
    quint64 id = 0;

    // When the handle is read from the payload
    const bool read = json_id(payload, &id);

    // Then the payload yields that id
    EXPECT_TRUE(read);
    EXPECT_EQ(id, 42U);
}

TEST(Handle, RejectsAPayloadWithoutALayerId) {
    // Given a payload that names no layer
    const QJsonObject payload{{"name", "points"}};
    quint64 id = 7;

    // When a handle is read from the payload
    const bool read = json_id(payload, &id);

    // Then nothing is read, and the caller's id is left as it was
    EXPECT_FALSE(read);
    EXPECT_EQ(id, 7U) << "a rejected handle must not be written";
}

TEST(Handle, RejectsEverythingThatIsNotAPositiveWholeNumber) {
    // Given values that look like handles but are not positive whole numbers
    quint64 id = 0;

    // When each is read as a handle
    // Then every one is rejected: ids start at 1, and a handle is a JSON number, not
    // text
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

TEST(Handle, RejectsWholeNumbersAboveTheExactIntegerRange) {
    // Given the largest exact JSON integer, and the next whole number a double can carry
    const double ceiling = static_cast<double>(kMaxExactJsonInteger);
    const double above = ceiling + 2.0;
    quint64 id = 0;

    // When each is read as a handle
    // Then the ceiling is a handle, and a whole number above it is not
    EXPECT_TRUE(handle_from_json(QJsonValue(ceiling), &id));
    EXPECT_FALSE(handle_from_json(QJsonValue(above), &id))
        << "a whole number above 2^53 cannot be carried exactly as a JSON number";
}

/// Given any whole number above the exact-integer range, it is never a handle.
/// Such a number was already rounded by the JSON parser, so accepting it lets
/// one id alias another.
RC_GTEST_PROP(Handle, RejectsWholeIdsAboveTheExactIntegerRange, ()) {
    // Given a generated whole number just above 2^53, in steps the double carries
    // exactly
    const auto steps = *rc::gen::inRange<std::uint64_t>(1, 1ULL << 40U);
    const double number =
        static_cast<double>(kMaxExactJsonInteger) + 2.0 * static_cast<double>(steps);

    // When it is read as a handle
    quint64 parsed = 0;

    // Then it is rejected
    RC_ASSERT(!handle_from_json(QJsonValue(number), &parsed));
}

/// Given any id the manager can hand out, the id survives a round trip through
/// a JSON number. The ceiling is the double mantissa, which is why the
/// registry's ids are checked against it rather than against `UINT64_MAX`.
RC_GTEST_PROP(Handle, EveryRepresentableIdRoundTrips, ()) {
    // Given a generated id in the exact-integer range [1, 2^53]
    const auto original = *rc::gen::inRange<std::uint64_t>(1, kMaxExactJsonInteger + 1);

    // When it is written as a JSON number and read back as a handle
    quint64 parsed = 0;
    const bool read =
        json_id(QJsonObject{{"layer_id", static_cast<double>(original)}}, &parsed);

    // Then the handle is read and equals the original id
    RC_ASSERT(read);
    RC_ASSERT(parsed == original);
}

/// Given any fractional number, it is never a handle, whatever its magnitude.
RC_GTEST_PROP(Handle, RejectsFractionalIds, ()) {
    // Given a generated whole part with a non-zero thousandths fraction
    const auto whole = *rc::gen::inRange<std::uint64_t>(1, 1ULL << 40U);
    const auto fraction = *rc::gen::inRange(1, 999);
    const double number =
        static_cast<double>(whole) + (static_cast<double>(fraction) / 1000.0);

    // When it is read as a handle
    quint64 parsed = 0;

    // Then it is rejected
    RC_ASSERT(!handle_from_json(QJsonValue(number), &parsed));
}

// ── the buffer that crosses the C ABI ───────────────────────────────────────

TEST(ResponseBuffer, IsNulTerminatedAndIndependentOfItsSource) {
    // Given a response string the manager is about to hand across the ABI
    std::string source = R"({"ok":true})";

    // When it is copied into a caller-owned buffer and the source is discarded
    char* copy = copy_response(source);
    ASSERT_NE(copy, nullptr);
    source.clear();

    // Then the copy still reads the full response, followed by a NUL terminator
    EXPECT_STREQ(copy, R"({"ok":true})");
    free_response(copy);
}

TEST(ResponseBuffer, FreeingNothingIsSafe) {
    // Given no buffer at all, as qgis_free receives for a null response
    // When it is released
    free_response(nullptr);

    // Then the call returns; reaching the end of this test is the proof
}

/// Given any response, every byte is copied and one NUL is appended: the Rust
/// side reads the buffer with `CStr`, so a missing terminator is an
/// out-of-bounds read and a short copy is a truncated answer.
RC_GTEST_PROP(ResponseBuffer, CopiesEveryByteAndTerminates,
              (const std::string& response)) {
    // Given a generated response
    // When it is copied across the ABI
    char* copy = copy_response(response);
    RC_ASSERT(copy != nullptr);

    const bool identical = std::memcmp(copy, response.data(), response.size()) == 0;
    const bool terminated = copy[response.size()] == '\0';
    free_response(copy);

    // Then every byte matches and the terminator follows the last one
    RC_ASSERT(identical);
    RC_ASSERT(terminated);
}

}  // namespace
