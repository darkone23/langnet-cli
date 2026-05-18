export function componentGlossFromCli(displayGloss: string, evidenceGloss: string) {
	const display = displayGloss.trim();
	const evidence = evidenceGloss.trim();

	if (!display) return evidence;
	if (evidence.length > display.length + 8) return evidence;
	return display;
}
