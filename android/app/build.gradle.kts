plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
android {
    namespace = "org.unovyra.uno"
    compileSdk = 35
    ndkVersion = "27.2.12479018"
    defaultConfig {
        applicationId = "org.unovyra.uno.scaffold"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0-skeleton"
        resValue("string", "uno_app_label", "UNOVYRA UNO · Scaffold")
        ndk { abiFilters += listOf("arm64-v8a") }
        externalNativeBuild {
            cmake {
                arguments += listOf(
                    "-DCMAKE_BUILD_TYPE=Release",
                    "-DGGML_NATIVE=OFF",
                    "-DGGML_OPENMP=OFF",
                    "-DGGML_LLAMAFILE=OFF",
                    "-DGGML_CPU_KLEIDIAI=OFF",
                    "-DGGML_BACKEND_DL=OFF",
                    "-DGGML_CPU_ALL_VARIANTS=OFF",
                    "-DLLAMA_CURL=OFF",
                    "-DLLAMA_OPENSSL=OFF",
                    "-DLLAMA_BUILD_TESTS=OFF",
                    "-DLLAMA_BUILD_EXAMPLES=OFF",
                    "-DLLAMA_BUILD_SERVER=OFF",
                    "-DLLAMA_BUILD_COMMON=OFF",
                    "-DBUILD_SHARED_LIBS=ON"
                )
            }
        }
    }
    externalNativeBuild {
        cmake {
            path = file("src/main/cpp/CMakeLists.txt")
            version = "3.22.1"
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    buildTypes {
        getByName("release") { isMinifyEnabled = false }
        getByName("debug") {
            val isolatedSuffix = providers.gradleProperty("unoIsolatedDebugSuffix").orNull
            if (isolatedSuffix != null) {
                require(Regex("ci[0-9]{5,20}").matches(isolatedSuffix)) {
                    "unoIsolatedDebugSuffix must be a CI run ID, e.g. ci42488780925"
                }
                applicationIdSuffix = ".$isolatedSuffix"
                versionNameSuffix = "-$isolatedSuffix"
                resValue("string", "uno_app_label", "UNO TEST · $isolatedSuffix")
            }
        }
    }
}
dependencies { implementation(project(":core")) }
