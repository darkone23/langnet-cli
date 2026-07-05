import type { ToolId } from '../search-data';

type ToolLike = {
	id: ToolId;
};

export function allAvailableToolIds(tools: readonly ToolLike[]) {
	return tools.map(({ id }) => id);
}

export function liveVisibleToolsForLookupTools(lookupTools: ToolId[], returnedToolIds: ToolId[]) {
	return returnedToolIds.filter((tool) => lookupTools.includes(tool));
}

export function nextLookupTools(currentTools: ToolId[], tool: ToolId) {
	if (currentTools.includes(tool)) {
		if (currentTools.length === 1) return currentTools;
		return currentTools.filter((candidate) => candidate !== tool);
	}
	return [...currentTools, tool];
}

export function nextVisibleTools(currentTools: ToolId[], tool: ToolId) {
	if (currentTools.includes(tool)) {
		if (currentTools.length === 1) return currentTools;
		return currentTools.filter((candidate) => candidate !== tool);
	}
	return [...currentTools, tool];
}
