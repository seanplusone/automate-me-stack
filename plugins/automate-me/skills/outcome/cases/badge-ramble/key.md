# Key: badge-ramble

A synthetic case. The app and the widget are invented. Never show this file to the skill.

This is a build brief for a small UI widget. Output says where it lives and what shares that space: the bell in the top bar, the avatar menu's dropdown that covers it, the tooltip, and its states. The speaker never says what shows while the count loads, or what the badge does on a narrow screen. The brief must ask, not assume. The pulse is a tangent.

## Facts, in the speaker's words

Fact: bell
Fact: top bar
Fact: avatar menu
Fact: tooltip
Fact: 99+

## Slots

Slot: Kind | build
Slot: Output | bell | dropdown | tooltip | states
Slot: Done | zero | 99+
Slot: Verification | browser

## Gaps that must be asked, not guessed

Unknown: loading | loading/loads
Unknown: narrow screen | narrow/mobile/width

## Guesses that fail the run

Forbidden: loading state invented | \b(spinner|skeleton|shows a dash)\b

## Parking lot

Parking: pulse | pulse
