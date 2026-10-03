#pragma once

#include <cstdint>

#if defined(__GNUC__) || defined(__clang__)
#define QGIS_MANAGER_API __attribute__((visibility("default")))
#else
#define QGIS_MANAGER_API
#endif

#ifdef __cplusplus
extern "C" {
#endif

/// Invoke the native manager with one UTF-8 JSON request and receive one
/// manager-owned UTF-8 JSON response. The response is never a QGIS pointer.
QGIS_MANAGER_API char* qgis_invoke(const char* request_json) noexcept;

/// Release a response returned by qgis_invoke.
QGIS_MANAGER_API void qgis_free(char* response_json) noexcept;

/// Return the version of the JSON transport without starting QGIS.
QGIS_MANAGER_API std::uint32_t qgis_transport_version() noexcept;

#ifdef __cplusplus
}
#endif

#undef QGIS_MANAGER_API
