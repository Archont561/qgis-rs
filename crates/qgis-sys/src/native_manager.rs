#[cfg(feature = "qgis")]
use std::{
    ffi::{CStr, CString},
    os::raw::c_char,
};

pub use qgis_protocol::TRANSPORT_VERSION as MANAGER_TRANSPORT_VERSION;

#[cfg(feature = "qgis")]
unsafe extern "C" {
    fn qgis_invoke(request_json: *const c_char) -> *mut c_char;
    fn qgis_free(response_json: *mut c_char);
    fn qgis_transport_version() -> u32;
}

fn error_response(kind: &str, error: &str) -> String {
    format!(
        r#"{{"transport_version":{},"ok":false,"result":{{"kind":"{}","error":"{}"}}}}"#,
        MANAGER_TRANSPORT_VERSION, kind, error
    )
}

/// Send one JSON request through the native QGIS manager and return its JSON
/// response.
///
/// The request is copied into a `CString` before entering the C ABI. The
/// response pointer is always released with the manager's paired `qgis_free`
/// function before this returns.
#[cfg(feature = "qgis")]
#[must_use]
pub fn invoke(request: &str) -> String {
    let request = match CString::new(request) {
        Ok(request) => request,
        Err(_) => return error_response("invalid_request", "request contains a NUL byte"),
    };

    // SAFETY: the C ABI only reads the NUL-terminated request during the call,
    // and returns a buffer whose ownership is transferred to this wrapper.
    let response_ptr = unsafe { qgis_invoke(request.as_ptr()) };
    if response_ptr.is_null() {
        return error_response("internal", "native manager returned a null response");
    }

    // SAFETY: qgis_invoke returns a valid NUL-terminated UTF-8 JSON buffer;
    // qgis_free is the matching release function for that exact pointer.
    let response = unsafe { CStr::from_ptr(response_ptr) }
        .to_string_lossy()
        .into_owned();
    // SAFETY: response_ptr is the pointer returned by qgis_invoke and has not
    // been released yet.
    unsafe { qgis_free(response_ptr) };
    response
}

#[cfg(not(feature = "qgis"))]
#[must_use]
pub fn invoke(_request: &str) -> String {
    error_response(
        "backend_unavailable",
        "this build was compiled without the QGIS backend",
    )
}

/// Return the native manager's transport version without starting QGIS.
#[cfg(feature = "qgis")]
#[must_use]
pub fn transport_version() -> u32 {
    // SAFETY: this function has no pointer arguments and is a pure version
    // query by contract.
    unsafe { qgis_transport_version() }
}

#[cfg(not(feature = "qgis"))]
#[must_use]
pub const fn transport_version() -> u32 {
    MANAGER_TRANSPORT_VERSION
}
