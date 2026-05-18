import assert from 'node:assert/strict';
import { buildComponentHeadwordDisplay, buildHeadwordDisplay } from './headword-display';

const sanskritDisplay = buildHeadwordDisplay({
	language: 'san',
	lexeme: 'puraa.na',
	source: 'dico',
	dictionary: 'dico',
	groupValues: ['puraa.na'],
	anchors: [
		{
			source: 'dico',
			dictionary: 'dico',
			query: 'purana',
			canonical_key: 'puraa.na',
			canonical_name: 'पुराण',
			source_name: 'पुराण'
		}
	]
});

assert.deepEqual(sanskritDisplay, {
	primary: 'पुराण',
	primaryLang: 'sa-Deva',
	title: {
		script: 'devanagari',
		initial: 'पु',
		rest: 'राण'
	},
	forms: [
		{ label: 'roman', value: 'purana' },
		{ label: 'key', value: 'puraa.na', kind: 'code' }
	]
});

const dattaDisplay = buildHeadwordDisplay({
	language: 'san',
	lexeme: 'datta',
	source: 'dico',
	dictionary: 'dico',
	groupValues: ['datta'],
	anchors: [
		{
			source: 'dico',
			dictionary: 'dico',
			query: 'datta',
			canonical_key: 'datta',
			canonical_name: 'दत्त',
			source_name: 'datta'
		}
	]
});

assert.deepEqual(dattaDisplay, {
	primary: 'दत्त',
	primaryLang: 'sa-Deva',
	title: {
		script: 'devanagari',
		initial: 'द',
		rest: 'त्त'
	},
	forms: [{ label: 'roman', value: 'datta' }]
});

const sanskritRomanFallbackDisplay = buildHeadwordDisplay({
	language: 'san',
	lexeme: 'aṣṭāṅga',
	source: 'cdsl',
	dictionary: 'MW',
	groupValues: ['azwanga', 'aṣṭāṅga'],
	anchors: [
		{
			source: 'cdsl',
			dictionary: 'mw',
			query: 'aṣṭan',
			canonical_key: 'ashtan',
			canonical_name: 'अष्टन्',
			source_name: 'azwan'
		},
		{
			source: 'cdsl',
			dictionary: 'mw',
			query: 'aṅga_1',
			canonical_key: 'aga',
			canonical_name: 'अग',
			source_name: 'aga'
		}
	]
});

assert.deepEqual(sanskritRomanFallbackDisplay, {
	primary: 'अष्टाङ्ग',
	primaryLang: 'sa-Deva',
	title: {
		script: 'devanagari',
		initial: 'अ',
		rest: 'ष्टाङ्ग'
	},
	forms: [{ label: 'roman', value: 'aṣṭāṅga' }]
});

const componentDhatriDisplay = buildComponentHeadwordDisplay({
	language: 'san',
	label: 'dhātrī'
});

assert.deepEqual(componentDhatriDisplay, {
	primary: 'धात्री',
	primaryLang: 'sa-Deva',
	title: {
		script: 'devanagari',
		initial: 'धा',
		rest: 'त्री'
	},
	forms: [{ label: 'roman', value: 'dhātrī' }]
});

const componentPutraDisplay = buildComponentHeadwordDisplay({
	language: 'san',
	label: 'putra'
});

assert.deepEqual(componentPutraDisplay, {
	primary: 'पुत्र',
	primaryLang: 'sa-Deva',
	title: {
		script: 'devanagari',
		initial: 'पु',
		rest: 'त्र'
	},
	forms: [{ label: 'roman', value: 'putra' }]
});

const componentDaDisplay = buildComponentHeadwordDisplay({
	language: 'san',
	label: 'da'
});

assert.deepEqual(componentDaDisplay, {
	primary: 'द',
	primaryLang: 'sa-Deva',
	title: {
		script: 'devanagari',
		initial: 'द',
		rest: ''
	},
	forms: [{ label: 'roman', value: 'da' }]
});

const componentDaaDisplay = buildComponentHeadwordDisplay({
	language: 'san',
	label: 'daa'
});

assert.deepEqual(componentDaaDisplay, {
	primary: 'दा',
	primaryLang: 'sa-Deva',
	title: {
		script: 'devanagari',
		initial: 'दा',
		rest: ''
	},
	forms: [{ label: 'roman', value: 'daa' }]
});

const genericComponentDisplay = buildComponentHeadwordDisplay({
	language: 'san',
	label: 'compound member'
});

assert.deepEqual(genericComponentDisplay, {
	primary: 'compound member',
	forms: []
});

const encodedLongRComponentDisplay = buildComponentHeadwordDisplay({
	language: 'san',
	label: 'k.rrta'
});

assert.deepEqual(encodedLongRComponentDisplay, {
	primary: 'कॄत',
	primaryLang: 'sa-Deva',
	title: {
		script: 'devanagari',
		initial: 'कॄ',
		rest: 'त'
	},
	forms: [{ label: 'roman', value: 'k.rrta' }]
});

const greekDisplay = buildHeadwordDisplay({
	language: 'grc',
	lexeme: 'logou',
	source: 'diogenes',
	dictionary: 'lsj',
	groupValues: ['logou', 'logos'],
	anchors: [
		{
			source: 'diogenes',
			dictionary: 'lsj',
			query: 'logos',
			canonical_key: 'logos',
			canonical_name: 'λόγος',
			source_name: 'λόγος'
		}
	]
});

assert.deepEqual(greekDisplay, {
	primary: 'λόγος',
	primaryLang: 'grc',
	title: {
		script: 'plain',
		initial: 'λ',
		rest: 'όγος'
	},
	forms: [
		{ label: 'key', value: 'logos', kind: 'code' },
		{ label: 'entry', value: 'logou', kind: 'code' }
	]
});

const greekUnicodeQueryDisplay = buildHeadwordDisplay({
	language: 'grc',
	lexeme: 'thaumazo',
	source: 'diogenes',
	dictionary: 'lsj',
	groupValues: ['thaumazo', 'θαυμάζω'],
	anchors: [
		{
			source: 'diogenes',
			dictionary: 'lsj',
			query: 'θαυμάζω',
			canonical_key: 'thaumazo',
			canonical_name: 'θαυμάζω',
			source_name: 'θαυμάζω'
		}
	]
});

assert.deepEqual(greekUnicodeQueryDisplay, {
	primary: 'θαυμάζω',
	primaryLang: 'grc',
	title: {
		script: 'plain',
		initial: 'θ',
		rest: 'αυμάζω'
	},
	forms: [{ label: 'key', value: 'thaumazo', kind: 'code' }]
});

const greekSingleGraphemeDisplay = buildHeadwordDisplay({
	language: 'grc',
	lexeme: 'ho',
	source: 'diogenes',
	dictionary: 'lsj',
	groupValues: ['ho'],
	anchors: [
		{
			source: 'diogenes',
			dictionary: 'lsj',
			query: 'ho',
			canonical_key: 'ho',
			canonical_name: 'ὁ',
			source_name: 'ὁ'
		}
	]
});

assert.deepEqual(greekSingleGraphemeDisplay, {
	primary: 'ὁ',
	primaryLang: 'grc',
	title: {
		script: 'plain',
		initial: 'ὁ',
		rest: ''
	},
	forms: [{ label: 'key', value: 'ho', kind: 'code' }]
});

const latinDisplay = buildHeadwordDisplay({
	language: 'lat',
	lexeme: 'nexus',
	source: 'gaffiot',
	dictionary: 'gaffiot',
	groupValues: ['nexus'],
	anchors: []
});

assert.deepEqual(latinDisplay, {
	primary: 'nexus',
	title: {
		script: 'plain',
		initial: 'n',
		rest: 'exus'
	},
	forms: []
});
