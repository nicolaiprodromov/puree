// Build script for the puree_rust_core Python extension module.
//
// With pyo3's `extension-module` feature the cdylib deliberately does NOT link
// libpython - the host interpreter provides the C-API when it imports the module.
// Linux accepts unresolved symbols in a shared library; macOS's linker refuses them
// unless told `-undefined dynamic_lookup`. pyo3 leaves emitting that flag to the
// crate (maturin adds it for you; a plain `cargo build` does not), so the macOS
// release builds failed at link time without this.
//
// `add_extension_module_link_args` emits `cargo:rustc-cdylib-link-arg=...`, which
// applies only to the cdylib target on Darwin (and emscripten) - a no-op everywhere
// else and for the `cargo test --no-default-features` executable.
fn main() {
    if std::env::var_os("CARGO_FEATURE_EXTENSION_MODULE").is_some() {
        pyo3_build_config::add_extension_module_link_args();
    }
}
