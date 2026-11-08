plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
android {
    namespace = "org.unovyra.uno"
    compileSdk = 35
    defaultConfig {
        applicationId = "org.unovyra.uno.scaffold"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0-skeleton"
        manifestPlaceholders["unoAppLabel"] = "UNOVYRA UNO · Scaffold"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    buildTypes {
        getByName("release") { isMinifyEnabled = false }
        getByName("debug") {
            // CI runners normally generate a fresh debug signing certificate. Using the
            // ordinary applicationId would conflict with an installed build signed by
            // an earlier runner and Android would refuse installation.
            //
            // Only an explicit CI-only suffix creates a side-by-side test application.
            // Default debug and release identities are unchanged.
            val isolatedSuffix = providers.gradleProperty("unoIsolatedDebugSuffix").orNull
            if (isolatedSuffix != null) {
                require(Regex("ci[0-9]{5,20}").matches(isolatedSuffix)) {
                    "unoIsolatedDebugSuffix must be a CI run ID, e.g. ci42488780925"
                }
                applicationIdSuffix = ".$isolatedSuffix"
                versionNameSuffix = "-$isolatedSuffix"
                // Launcher/app-switcher label must visibly differ from older APKs.
                manifestPlaceholders["unoAppLabel"] = "UNO TEST · $isolatedSuffix"
            }
        }
    }
}
dependencies { implementation(project(":core")) }
