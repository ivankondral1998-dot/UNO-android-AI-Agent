package org.unovyra.uno.core

import kotlin.math.pow

/** Visual UI preference only. It grants NO Android capabilities and changes NO neural weights. */
enum class ThemeTone { DARK, LIGHT }
enum class ThemeOrigin { OWNER_EXPLICIT, OWNER_REQUESTED_CREATIVE, OPT_IN_CONVERSATION_STYLE }
enum class ThemeReview { READY_FOR_CONFIRMATION, REJECTED_NOT_REQUESTED, REJECTED_NO_CONSENT, REJECTED_BAD_COLOR }

data class UnoTheme(val tone: ThemeTone, val accentRgb: Int) {
    init { require(accentRgb in 0..0xFFFFFF) }
}

data class UnoThemeProposal(
    val theme: UnoTheme,
    val origin: ThemeOrigin,
    /** Short generic justification; never store excerpts or sensitive inferred user traits here. */
    val reasonCode: String
)

/**
 * UI theme is a suggestion, not a neural capability, an identity inference or a permission.
 * The future single UNO F may propose a color; the trusted UI decides whether to display/apply it.
 * No transcript retention, network, neural weight edits, permissions, or silent theme changes.
 */
class UnoThemeGate(default: UnoTheme = UnoTheme(ThemeTone.DARK, 0xFF8D2A)) {
    var current: UnoTheme = default
        private set
    var pending: UnoThemeProposal? = null
        private set
    var conversationStyleConsent = false
        private set
    var manualOverride = false
        private set

    /** Revoking consent discards proposals which had used behavioral signals. */
    fun setConversationStyleConsent(allowed: Boolean) {
        conversationStyleConsent = allowed
        if (!allowed && pending?.origin == ThemeOrigin.OPT_IN_CONVERSATION_STYLE) pending = null
    }

    /** Require a fresh user request; the model may NEVER passively repaint the app. */
    fun suggest(ownerRequestedNow: Boolean, proposal: UnoThemeProposal): ThemeReview {
        if (!ownerRequestedNow) return ThemeReview.REJECTED_NOT_REQUESTED
        if (proposal.origin == ThemeOrigin.OPT_IN_CONVERSATION_STYLE && !conversationStyleConsent)
            return ThemeReview.REJECTED_NO_CONSENT
        if (proposal.reasonCode.isBlank() || proposal.reasonCode.length > 96 ||
            proposal.reasonCode.any { it == '\n' || it == '\r' }) return ThemeReview.REJECTED_BAD_COLOR
        pending = proposal.copy(theme = proposal.theme.copy(
            accentRgb = UnoThemeColors.accessibleAccent(proposal.theme.accentRgb, proposal.theme.tone)
        ))
        return ThemeReview.READY_FOR_CONFIRMATION
    }

    /** Only an explicit approval applies an AI proposal; an owner manual selection always wins. */
    fun confirmByOwner(): Boolean {
        val proposal = pending ?: return false
        if (proposal.origin == ThemeOrigin.OPT_IN_CONVERSATION_STYLE && !conversationStyleConsent) {
            pending = null
            return false
        }
        current = proposal.theme
        pending = null
        manualOverride = false
        return true
    }

    fun decline() { pending = null }

    fun setManually(theme: UnoTheme) {
        current = theme.copy(accentRgb = UnoThemeColors.accessibleAccent(theme.accentRgb, theme.tone))
        pending = null
        manualOverride = true
    }
}

object UnoThemeColors {
    const val ORANGE = 0xFF8D2A
    const val YELLOW = 0xF2C14E
    const val ROSE = 0xF57FA7
    const val CYAN = 0x6CCFE5

    fun background(tone: ThemeTone): Int = if (tone == ThemeTone.DARK) 0x10151F else 0xFAFBFD

    private fun linear(channel: Int): Double {
        val s = channel / 255.0
        return if (s <= 0.04045) s / 12.92 else ((s + 0.055) / 1.055).pow(2.4)
    }
    fun luminance(rgb: Int): Double {
        require(rgb in 0..0xFFFFFF)
        return 0.2126 * linear((rgb shr 16) and 255) +
            0.7152 * linear((rgb shr 8) and 255) + 0.0722 * linear(rgb and 255)
    }
    fun contrast(a: Int, b: Int): Double {
        val hi = maxOf(luminance(a), luminance(b))
        val lo = minOf(luminance(a), luminance(b))
        return (hi + 0.05) / (lo + 0.05)
    }
    private fun blend(a: Int, b: Int, step: Int): Int {
        val out = IntArray(3)
        for (i in 0..2) {
            val shift = 16 - i * 8
            val ac = (a shr shift) and 255
            val bc = (b shr shift) and 255
            out[i] = (ac * (100 - step) + bc * step) / 100
        }
        return (out[0] shl 16) or (out[1] shl 8) or out[2]
    }

    /** Normalize proposed RGB into readable accent text against fixed dark/light surfaces (WCAG >=4.5). */
    fun accessibleAccent(rgb: Int, tone: ThemeTone): Int {
        require(rgb in 0..0xFFFFFF)
        val bg = background(tone)
        val target = if (tone == ThemeTone.DARK) 0xFFFFFF else 0x000000
        for (step in 0..100) {
            val candidate = blend(rgb, target, step)
            if (contrast(candidate, bg) >= 4.5) return candidate
        }
        return target
    }
}
