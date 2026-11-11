plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
// Explicit local owner-update mode only. This does not sign or publish a release.
// Keystore/passwords are read from LOCAL environment, never committed or passed as -P.
val ownerUpdateId = providers.gradleProperty("unoOwnerUpdateApplicationId").orNull
val ownerUpdateCodeText = providers.gradleProperty("unoOwnerUpdateVersionCode").orNull
val ownerUpdateRequested = ownerUpdateId != null || ownerUpdateCodeText != null
val ownerUpdateCode = ownerUpdateCodeText?.toIntOrNull()
if (ownerUpdateRequested) {
    require(ownerUpdateId != null && ownerUpdateCode != null && ownerUpdateCode in 1..Int.MAX_VALUE) {
        "Owner signed build requires stable applicationId and positive versionCode"
    }
    require(Regex("org\\.unovyra\\.uno(?:\\.scaffold(?:\\.ci[0-9]{5,20})?)?").matches(ownerUpdateId)) {
        "Owner signed build applicationId is outside the UNO package family"
    }
    require(providers.environmentVariable("GITHUB_ACTIONS").orNull != "true") {
        "Owner update signing is local-only; CI artifacts are never owner updates"
    }
}
android {
    namespace = "org.unovyra.uno"
    compileSdk = 35
    ndkVersion = "27.2.12479018"
    defaultConfig {
        applicationId = ownerUpdateId ?: "org.unovyra.uno.scaffold"
        minSdk = 26
        targetSdk = 35
        versionCode = ownerUpdateCode ?: 1
        versionName = if (ownerUpdateRequested) "0.1.0-lab.$ownerUpdateCode" else "0.1.0-skeleton"
        resValue("string", "uno_app_label", if (ownerUpdateId == "org.unovyra.uno") "UNOVYRA UNO" else if (ownerUpdateRequested) "UNOVYRA UNO · Lab" else "UNOVYRA UNO · Scaffold")
        ndk { abiFilters += listOf("arm64-v8a") }
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
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
    if (ownerUpdateRequested) {
        val keyFile = providers.environmentVariable("UNO_OWNER_UPDATE_KEYSTORE").orNull
            ?: error("Missing local UNO_OWNER_UPDATE_KEYSTORE")
        require(file(keyFile).isFile) { "Local owner-update keystore is not a readable file" }
        signingConfigs.create("unoOwnerUpdate") {
            storeFile = file(keyFile)
            storePassword = providers.environmentVariable("UNO_OWNER_UPDATE_STORE_PASSWORD").orNull
            keyAlias = providers.environmentVariable("UNO_OWNER_UPDATE_KEY_ALIAS").orNull
            keyPassword = providers.environmentVariable("UNO_OWNER_UPDATE_KEY_PASSWORD").orNull
            require(!storePassword.isNullOrEmpty() && !keyAlias.isNullOrEmpty() &&
                !keyPassword.isNullOrEmpty()) { "Local owner-update signing credentials are missing" }
        }
    }
    buildTypes {
        getByName("release") { isMinifyEnabled = false }
        getByName("debug") {
            val isolatedSuffix = providers.gradleProperty("unoIsolatedDebugSuffix").orNull
            require(!ownerUpdateRequested || isolatedSuffix == null) {
                "Owner update cannot use a new CI suffix; install-over-existing only"
            }
            if (ownerUpdateRequested) {
                signingConfig = signingConfigs.getByName("unoOwnerUpdate")
            }
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
dependencies {
    implementation(project(":core"))
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test:runner:1.6.2")
}
