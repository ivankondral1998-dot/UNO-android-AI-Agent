package org.unovyra.uno

import android.graphics.drawable.GradientDrawable
import android.view.View
import android.widget.Button

/** Shared product chrome. Does not grant permissions or claim a loaded model. */
internal object UnoChrome {
    const val INK = 0xFFF4F1EA.toInt()
    const val MUTED = 0xFF9AA3AD.toInt()
    const val BG = 0xFF0E141B.toInt()
    const val SURFACE = 0xFF18222C.toInt()
    const val ACCENT = 0xFFE8943A.toInt()
    const val ACCENT_INK = 0xFF1A1208.toInt()

    fun dp(view: View, value: Int): Int =
        (value * view.resources.displayMetrics.density).toInt()

    fun round(color: Int, radiusPx: Float) = GradientDrawable().apply {
        cornerRadius = radiusPx
        setColor(color)
    }

    fun button(button: Button, fill: Int, text: Int) {
        val radius = 16f * button.resources.displayMetrics.density
        button.background = round(fill, radius)
        button.backgroundTintList = null
        button.setTextColor(text)
        button.isAllCaps = false
        button.stateListAnimator = null
        button.minHeight = dp(button, 52)
    }
}
