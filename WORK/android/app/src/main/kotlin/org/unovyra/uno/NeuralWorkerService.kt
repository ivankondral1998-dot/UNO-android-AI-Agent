package org.unovyra.uno

import android.app.Service
import android.content.Intent
import android.os.IBinder

/** Isolated process placeholder. No Binder contract, no inference, no permissions.
 * Cannot be mistaken for a working isolated neural worker until G5 implementation.
 */
class NeuralWorkerService: Service() {
    override fun onBind(intent: Intent?): IBinder? = null
}
