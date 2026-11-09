package org.unovyra.uno

/** Experimental llama.cpp JNI. It has no Android action/permission interface. */
internal fun interface UnoTokenReceiver {
    /** Full accumulated UTF-8 output, not a potentially incomplete UTF-8 token fragment. */
    fun onTokens(bytes: ByteArray)
}

internal object UnoNativeEngine {
    init { System.loadLibrary("uno_llama") }
    external fun load(path: String): Boolean
    external fun generate(
        roles: Array<String>,
        contents: Array<String>,
        maxTokens: Int,
        receiver: UnoTokenReceiver
    ): ByteArray?
    external fun resetCancel()
    external fun cancel()
    external fun unload()
}
