package org.unovyra.uno.core

object ThemePersonalizationTest {
    var pass = 0
        private set
    private fun verify(condition: Boolean) { check(condition); pass++ }
    fun run() {
        val dark = UnoTheme(ThemeTone.DARK, UnoThemeColors.ORANGE)
        val gate = UnoThemeGate(dark)
        val creative = UnoThemeProposal(UnoTheme(ThemeTone.DARK, UnoThemeColors.ROSE),
            ThemeOrigin.OWNER_REQUESTED_CREATIVE, "Creative option")
        verify(gate.current == dark)
        verify(gate.pending == null)
        verify(gate.suggest(false, creative) == ThemeReview.REJECTED_NOT_REQUESTED)
        verify(gate.pending == null)
        verify(!gate.confirmByOwner())
        verify(gate.suggest(true, creative) == ThemeReview.READY_FOR_CONFIRMATION)
        verify(gate.current == dark)
        verify(gate.pending != null)
        gate.decline()
        verify(gate.current == dark && gate.pending == null)
        val styled = UnoThemeProposal(UnoTheme(ThemeTone.LIGHT, UnoThemeColors.CYAN),
            ThemeOrigin.OPT_IN_CONVERSATION_STYLE, "Owner-permitted style cues")
        verify(gate.suggest(true, styled) == ThemeReview.REJECTED_NO_CONSENT)
        gate.setConversationStyleConsent(true)
        verify(gate.suggest(true, styled) == ThemeReview.READY_FOR_CONFIRMATION)
        verify(gate.current == dark)
        gate.setConversationStyleConsent(false)
        verify(gate.pending == null)
        verify(!gate.confirmByOwner())
        gate.setConversationStyleConsent(true)
        verify(gate.suggest(true, styled) == ThemeReview.READY_FOR_CONFIRMATION)
        verify(gate.confirmByOwner())
        verify(gate.current.tone == ThemeTone.LIGHT)
        verify(gate.pending == null)
        val manual = UnoTheme(ThemeTone.DARK, UnoThemeColors.YELLOW)
        gate.setManually(manual)
        verify(gate.manualOverride)
        verify(gate.current.accentRgb == UnoThemeColors.accessibleAccent(UnoThemeColors.YELLOW,ThemeTone.DARK))
        verify(gate.pending == null)
        verify(gate.suggest(true, creative) == ThemeReview.READY_FOR_CONFIRMATION)
        verify(gate.current != creative.theme)
        gate.setManually(manual)
        verify(!gate.confirmByOwner())
        val all = listOf(0x000000,0xFFFFFF,UnoThemeColors.ORANGE,UnoThemeColors.YELLOW,
                         UnoThemeColors.ROSE,UnoThemeColors.CYAN,0x777777,0x252525,0xB2A75D)
        for (color in all) for (tone in ThemeTone.values()) {
            val c=UnoThemeColors.accessibleAccent(color,tone)
            verify(UnoThemeColors.contrast(c,UnoThemeColors.background(tone))>=4.5)
            verify(c in 0..0xFFFFFF)
        }
        verify(gate.suggest(true,creative.copy(reasonCode=""))==ThemeReview.REJECTED_BAD_COLOR)
        verify(gate.suggest(true,creative.copy(reasonCode="a".repeat(97)))==ThemeReview.REJECTED_BAD_COLOR)
        println("UNO_THEME_HOST_PASS=$pass")
    }
}
