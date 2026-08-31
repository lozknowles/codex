use std::path::PathBuf;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("cargo:rustc-check-cfg=cfg(codex_bazel)");
    println!("cargo:rerun-if-changed=src/grpc");

    let mut config = tonic_prost_build::Config::new();
    // Termux supplies a trusted native `protoc`, while protoc-bin-vendored
    // does not publish an Android/aarch64 artifact. Keep the vendored path
    // for desktop builds and allow explicit PROTOC selection everywhere.
    let protoc = std::env::var_os("PROTOC")
        .map(PathBuf::from)
        .or_else(|| {
            if cfg!(target_os = "android") {
                Some(PathBuf::from("protoc"))
            } else {
                None
            }
        })
        .unwrap_or(protoc_bin_vendored::protoc_bin_path()?);
    config.protoc_executable(protoc);
    let proto_files = glob::glob("src/grpc/*.proto")?.collect::<Result<Vec<_>, _>>()?;

    tonic_prost_build::configure()
        .build_client(/*enable*/ true)
        .build_server(/*enable*/ true)
        .compile_with_config(config, &proto_files, &[PathBuf::from("src/grpc")])?;

    Ok(())
}
