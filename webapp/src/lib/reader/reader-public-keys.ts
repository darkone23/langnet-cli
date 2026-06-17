import type { ReaderSourceIndexItem, ReaderWork } from './index';

export function readerIsDeprecatedWorkRef(value: string | null | undefined) {
	return /^urn:cts:(?:latinLit|greekLit|sanskritLit):/u.test(value ?? '');
}

function readerPublicKeyChecksum(value: string) {
	let hash = 5381;
	for (let index = 0; index < value.length; index += 1) {
		hash = (hash * 33) ^ value.charCodeAt(index);
	}
	return (hash >>> 0).toString(36).slice(0, 6);
}

function readerPublicKeySlug(value: string) {
	return (
		value
			.normalize('NFKD')
			.replace(/[\u0300-\u036f]/g, '')
			.toLowerCase()
			.replace(/[^a-z0-9]+/g, '-')
			.replace(/^-+|-+$/g, '')
			.slice(0, 48) || 'work'
	);
}

function readerWorkPublicAuthor(work: ReaderWork) {
	return (
		work.canonical_author_name?.trim() ||
		work.source_author?.trim() ||
		work.author?.trim() ||
		'Unknown'
	);
}

export function readerWorkPublicKey(work: ReaderWork) {
	const author = readerPublicKeySlug(readerWorkPublicAuthor(work));
	const title = readerPublicKeySlug(work.title?.trim() || 'untitled');
	const seed = [work.canonical_text_id, work.canonical_address, work.work_id, work.source_id]
		.filter(Boolean)
		.join('|');
	return `${author}-${title}--${readerPublicKeyChecksum(seed || `${author}|${title}`)}`;
}

export function readerSourceIndexPublicKey(item: ReaderSourceIndexItem) {
	const author = readerPublicKeySlug(item.author || 'unknown');
	const title = readerPublicKeySlug(item.title || item.edition_label || 'untitled');
	const seed = [
		item.canonical_text_id,
		item.work_id,
		item.source_id,
		item.edition_id,
		item.source_hash
	]
		.filter(Boolean)
		.join('|');
	return `${author}-${title}--${readerPublicKeyChecksum(seed || `${author}|${title}`)}`;
}
