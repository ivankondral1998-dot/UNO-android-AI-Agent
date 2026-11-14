plugins { id("org.jetbrains.kotlin.jvm") }
kotlin { jvmToolchain(17) }

// Existing tests use a top-level main, not JUnit. Without this task, Gradle
// :core:test would report success while executing zero UNO self-tests.
tasks.register<JavaExec>("unoHostTests") {
    group = "verification"
    description = "Compile and run the existing UNO host self-test harness"
    dependsOn(tasks.named("testClasses"))
    classpath = sourceSets["test"].runtimeClasspath
    mainClass.set("org.unovyra.uno.core.AllHostTestsKt")
}