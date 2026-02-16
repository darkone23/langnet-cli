import re
from collections import defaultdict
from dataclasses import dataclass, field
from string import digits
from typing import TypedDict

import betacode.conv
import cattrs
import requests
import structlog
from bs4 import BeautifulSoup, FeatureNotFound, Tag
from langnet.citation.cts_urn import CTSUrnMapper

# from langnet.citation.models import Citation, CitationCollection, CitationType

logger = structlog.get_logger(__name__)

PERSEUS_MORPH_PART_COUNT = 2
MAX_NON_DOT_CHARS = 4
HTTP_OK_STATUS = 200

DiogenesChunkT = dataclass


@dataclass
class NoMatchFoundHeader:
    logeion: str
    chunk_type: str = field(default="NoMatchFoundHeader")


@dataclass
class PerseusMorphTerm:
    stem: list[str]
    tags: list[str]
    defs: list[str] | None = field(default=None)


@dataclass
class PerseusMorphology:
    morphs: list[PerseusMorphTerm]
    warning: str | None = field(default=None)


@dataclass
class PerseusAnalysisHeader:
    logeion: str
    morphology: PerseusMorphology
    chunk_type: str = field(default="PerseusAnalysisHeader")


@dataclass
class DiogenesDefinitionBlock:
    entry: str
    entryid: str
    # senses: list[str] | None = field(default=None)
    citations: dict | None = field(default=None)
    heading: str | None = field(default=None)
    diogenes_warning: str | None = field(default=None)


@dataclass
class DiogenesDefinitionEntry:
    blocks: list[DiogenesDefinitionBlock]
    term: str


@dataclass
class DiogenesFuzzyReference:
    reference_id: str
    definitions: DiogenesDefinitionEntry
    chunk_type: str = field(default="DiogenesFuzzyReference")


@dataclass
class UnknownChunkType:
    soup: str
    chunk_type: str = field(default="UnknownChunkType")


@dataclass
class DiogenesMatchingReference:
    reference_id: str
    definitions: DiogenesDefinitionEntry
    chunk_type: str = field(default="DiogenesMatchingReference")


@dataclass
class DiogenesResultT:
    chunks: list[
        PerseusAnalysisHeader
        | NoMatchFoundHeader
        | DiogenesMatchingReference
        | DiogenesFuzzyReference
        | UnknownChunkType
    ]
    dg_parsed: bool
    chunk_types: list[str]
    is_fuzzy_overall: bool = field(default=False)


class ParsedMorphEntry(TypedDict, total=False):
    stem: list[str]
    tags: list[str]
    defs: list[str]


class ParsedMorphology(TypedDict, total=False):
    morphs: list[ParsedMorphEntry]
    warning: str


class ParseResultDraft(TypedDict, total=False):
    chunks: list[
        PerseusAnalysisHeader
        | NoMatchFoundHeader
        | DiogenesMatchingReference
        | DiogenesFuzzyReference
        | UnknownChunkType
    ]
    dg_parsed: bool
    is_fuzzy_overall: bool
    chunk_types: list[str]


class ChunkDraft(TypedDict, total=False):
    soup: BeautifulSoup
    chunk_type: str
    is_fuzzy_match: bool
    logeion: str
    reference_id: str
    morphology: PerseusMorphology | ParsedMorphology
    definitions: DiogenesDefinitionEntry


class DiogenesChunkType:
    NoMatchFoundHeader = "NoMatchFoundHeader"

    PerseusAnalysisHeader = "PerseusAnalysisHeader"

    DiogenesFuzzyReference = "DiogenesFuzzyReference"

    DiogenesMatchingReference = "DiogenesMatchingReference"

    UnknownChunkType = "UnknownChunkType"


class DiogenesLanguages:
    GREEK = "grk"
    LATIN = "lat"

    parse_langs = set([GREEK, LATIN])

    @staticmethod
    def greek_to_code(greek):
        code = betacode.conv.uni_to_beta(greek)
        return code.translate(
            str.maketrans("", "", digits)
        )  # remove digits from betacode since diogenes does better without them....

    @staticmethod
    def code_to_greek(beta):
        return betacode.conv.beta_to_uni(beta)


class DiogenesScraper:
    "data refinement layer and client for diogenes"

    _PARSER_PREFERENCE = ("lxml", "html5lib", "html.parser")

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url

        if self.base_url is None:
            self.base_url = "http://localhost:8888/"

        if not self.base_url.endswith("/"):
            self.base_url += "/"

    def _make_soup(self, html: str) -> BeautifulSoup:
        for parser in self._PARSER_PREFERENCE:
            try:
                return BeautifulSoup(html, parser)
            except FeatureNotFound:
                continue
        return BeautifulSoup(html, "html.parser")

    def __diogenes_parse_url(self, word, lang):
        url = f"{self.base_url}Perseus.cgi?do=parse&lang={lang}&q={word}"
        return url

    def extract_parentheses_text(self, text):
        extracted = " ".join(
            re.findall(r"\((.*?)\)", text, re.DOTALL)
        )  # Extract text inside parentheses, including newlines
        cleaned_text = re.sub(
            r"\s*\(.*?\)\s*", " ", text, flags=re.DOTALL
        ).strip()  # Remove parentheses and enclosed text

        logger.debug(
            "extract_parentheses_text",
            original_len=len(text),
            extracted_len=len(extracted),
        )
        return cleaned_text, extracted

    def find_nd_coordinate(self, event_id: str):
        """
        translate padding indent histories into n-dimensional array coordinates
        """
        try:
            values = list(map(int, event_id.split(":")))  # Convert to integer list
        except ValueError as e:
            logger.error("find_nd_coordinate_parse_failed", event_id=event_id, error=str(e))
            raise

        unique_values = list(dict.fromkeys(values))  # Determine hierarchy
        level_counters = defaultdict(int)  # Track occurrences at each depth
        coordinates = []

        stack = []  # Keeps track of the active hierarchy levels

        for i, value in enumerate(values):
            dimension_index = unique_values.index(value)

            # Trim stack to the correct depth
            stack = stack[:dimension_index]

            # Get the count of how many times this exact hierarchy exists
            count = level_counters[tuple(stack)]  # Count occurrences of parent structure
            level_counters[tuple(stack)] += 1  # Increment count for this structure

            # Append new index to the coordinate
            stack.append(count)
            coordinates.append(tuple(stack))  # Store the computed coordinate

        logger.debug("find_nd_coordinate", event_id=event_id, result=coordinates[-1])
        return coordinates[-1]  # Return the last computed coordinate

    def _parse_perseus_morph(self, tag: Tag) -> ParsedMorphEntry:
        perseus_morph = tag.get_text()
        parts = perseus_morph.split(":")
        assert len(parts) == PERSEUS_MORPH_PART_COUNT, (
            f"Perseus morphology should split stem from tags: [{parts}]"
        )
        [stems, tag_parts] = parts

        cleaned_defs = []
        cleaned_stems = []
        stem_part, maybe_def = self.extract_parentheses_text(stems)
        for word_def in maybe_def.split(","):
            cleaned_def = re.sub(r"\d+", "", word_def).strip()
            if cleaned_def:
                cleaned_defs.append(cleaned_def)
        for perseus_stem in stem_part.split(","):
            cleaned_stems.append(re.sub(r"\d+", "", perseus_stem).strip())

        cleaned_tags = []
        tag_parts = re.sub(r"[()]+", "", tag_parts)
        for t in tag_parts.replace("/", " ").split():
            pos = t.strip()
            if pos not in cleaned_tags:
                cleaned_tags.append(pos)

        morph: ParsedMorphEntry = {"stem": cleaned_stems, "tags": cleaned_tags}
        if cleaned_defs:
            morph["defs"] = cleaned_defs
        return morph

    def handle_morphology(self, soup: BeautifulSoup) -> ParsedMorphology:
        morphs: list[ParsedMorphEntry] = []
        maybe_morph_els: list[Tag] = []
        warning: str | None = None
        for tag in soup.find_all("li"):
            maybe_morph_els.append(tag)
        for tag in soup.find_all("p"):
            if len(maybe_morph_els) == 0:
                maybe_morph_els.append(tag)
            else:
                warning = tag.get_text()
                logger.debug("handle_morphology_warning", warning_text=warning[:100])

        logger.debug(
            "handle_morphology",
            li_count=len(maybe_morph_els),
            p_count=len(soup.find_all("p")),
        )

        for tag in maybe_morph_els:
            morphs.append(self._parse_perseus_morph(tag))

        morph_dict: ParsedMorphology = {"morphs": morphs}

        if warning:
            _nothing, warning_txt = self.extract_parentheses_text(warning)
            morph_dict["warning"] = warning_txt

        logger.debug("handle_morphology_completed", morph_count=len(morphs))
        return morph_dict

    def _extract_heading_from_b(self, b_tag) -> tuple[str | None, bool]:
        initial_text = b_tag.get_text().strip().rstrip(",").rstrip(":")
        chars = set()
        dot = set(["."])
        for char in initial_text:
            chars.add(char)
            if len(chars - dot) > MAX_NON_DOT_CHARS:
                return None, False
        if initial_text.endswith(".") and len(chars - dot) <= MAX_NON_DOT_CHARS:
            return initial_text, True
        return None, False

    def _normalize_text_for_comparison(self, text: str) -> str:
        normalized = text.strip()
        if normalized.endswith("."):
            normalized = normalized[:-1]
        return normalized.rstrip(",").rstrip(":")

    # def _collect_senses(self, soup: BeautifulSoup) -> list[str]:
    #     b_tags = soup.select("b")
    #     heading_texts = set()

    #     for b in b_tags:
    #         heading, is_heading = self._extract_heading_from_b(b)
    #         if is_heading and heading:
    #             heading_texts.add(self._normalize_text_for_comparison(b.get_text()))

    #     non_heading_tags = [
    #         b
    #         for b in b_tags
    #         if self._normalize_text_for_comparison(b.get_text()) not in heading_texts
    #     ]

    #     senses = []
    #     for b in non_heading_tags:
    #         raw_text = b.get_text()
    #         sense_txt = self._normalize_text_for_comparison(raw_text)

    #         if "(" in sense_txt and ")" not in sense_txt:
    #             sense_txt += ")"
    #         senses.append(sense_txt)
    #     return senses

    # def _deduplicate_senses(self, senses: list[str]) -> list[str]:
    #     unique = []
    #     for sense in senses:
    #         if sense not in unique:
    #             unique.append(sense)
    #     return unique

    def _process_block(self, block: dict, soup: BeautifulSoup, indent_history: list):
        for p in soup.select("p"):
            _nothing, warning = self.extract_parentheses_text(p.get_text())
            block["diogenes_warning"] = warning.replace("\n", " ")
            p.decompose()

        refs = {}
        for ref in soup.select(".origjump"):
            ref_id = " ".join(ref.attrs.get("class", [])).strip("origjump ").lower()
            # ref_id = CTSUrnMapper.map_perseus_to_urn(ref_id)
            ref_txt = ref.get_text()
            canon_name = CTSUrnMapper.map_perseus_to_urn(ref_id)
            if canon_name:
                refs[canon_name] = ref_txt
            else:
                refs[ref_id] = ref_txt
        if len(refs.items()) > 0:
            # converted_citations = []
            # for urn, citation_text in refs.items():
            block["citations"] = refs
            # CitationCollection(citations=converted_citations)
            logger.debug("handle_references_citations", count=len(refs))

        # senses = self._collect_senses(soup)
        # senses_cleaned = self._deduplicate_senses(senses)
        # if len(senses_cleaned) > 0:
        #     block["senses"] = senses_cleaned

        block_txt = soup.get_text().strip().rstrip(",")

        block["entry"] = f"{block_txt}"
        coords = self.find_nd_coordinate(block["indentid"])

        block["entryid"] = ":".join([str(i).zfill(2) for i in coords])
        del block["indentid"]
        del block["soup"]

    def handle_references(self, soup):
        references = dict()

        for term in soup.select("h2 > span:first-child"):
            references["term"] = term.get_text()

        for term in soup.select("h2"):
            term.decompose()

        blocks = []
        indent_history = [0]

        def shift_cursor(block: BeautifulSoup):
            css_text: str = str(block.attrs.get("style", ""))
            css_match = re.search(r"padding-left:\s*([\d.]+)", css_text)
            indent = 0
            if css_match:
                indent = int(css_match.group(1))
            indent_history.append(indent)
            return ":".join([str(i).zfill(2) for i in indent_history])

        def insert_block(block: BeautifulSoup):
            block_copy = self._make_soup(f"{block}")
            node_id = shift_cursor(block)
            blocks.append(dict(indentid=node_id, soup=block_copy))

        def insert_root_node(block: BeautifulSoup):
            node_id = "0".zfill(2)
            next_blocks = [dict(indentid=node_id, soup=block)] + blocks
            blocks.clear()
            for obj in next_blocks:
                blocks.append(obj)

        for block in soup.select("#sense"):
            insert_block(block)
            block.decompose()

        insert_root_node(soup)

        for block in blocks:
            self._process_block(block, block["soup"], indent_history)

        references["blocks"] = blocks

        logger.debug("handle_references_completed", block_count=len(blocks))
        return references

    def process_chunk(self, result: ParseResultDraft, chunk: ChunkDraft) -> None:
        soup: BeautifulSoup = chunk["soup"]
        chunk_type: str = chunk["chunk_type"]

        logger.debug("process_chunk", chunk_type=chunk_type)

        if chunk_type == DiogenesChunkType.PerseusAnalysisHeader:
            self._process_morphology_chunk(chunk, soup)
            morphology_obj = chunk.get("morphology")
            if isinstance(morphology_obj, PerseusMorphology):
                morphology = morphology_obj
            elif isinstance(morphology_obj, dict):
                morphology = cattrs.structure(morphology_obj, PerseusMorphology)
            else:
                morphology = PerseusMorphology(morphs=[], warning=None)
            result["chunks"].append(
                PerseusAnalysisHeader(logeion=chunk.get("logeion", ""), morphology=morphology)
            )
        elif chunk_type == DiogenesChunkType.NoMatchFoundHeader:
            result["chunks"].append(NoMatchFoundHeader(logeion=chunk.get("logeion", "")))
        elif chunk_type == DiogenesChunkType.DiogenesMatchingReference:
            self._process_reference_chunk(chunk, soup)
            definitions_obj = chunk.get("definitions")
            if isinstance(definitions_obj, DiogenesDefinitionEntry):
                definitions = definitions_obj
            else:
                definitions = DiogenesDefinitionEntry(blocks=[], term="")
            result["chunks"].append(
                DiogenesMatchingReference(
                    reference_id=chunk.get("reference_id", ""), definitions=definitions
                )
            )
        elif chunk_type == DiogenesChunkType.DiogenesFuzzyReference:
            self._process_reference_chunk(chunk, soup)
            definitions_obj = chunk.get("definitions")
            if isinstance(definitions_obj, DiogenesDefinitionEntry):
                definitions = definitions_obj
            else:
                definitions = DiogenesDefinitionEntry(blocks=[], term="")
            result["chunks"].append(
                DiogenesFuzzyReference(
                    reference_id=chunk.get("reference_id", ""), definitions=definitions
                )
            )
        else:
            logger.debug("process_chunk_unknown_type", chunk_type=chunk_type)
            soup_str = str(soup) if soup else ""
            result["chunks"].append(UnknownChunkType(soup=soup_str))

        # Clean up temporary keys
        chunk.pop("soup", None)
        chunk.pop("is_fuzzy_match", None)
        chunk.pop("logeion", None)
        chunk.pop("reference_id", None)
        chunk.pop("morphology", None)
        chunk.pop("definitions", None)
        chunk.pop("logeion", None)
        chunk.pop("reference_id", None)
        chunk.pop("morphology", None)
        chunk.pop("definitions", None)

    def _process_morphology_chunk(self, chunk, soup):
        """Process morphology chunk."""
        morph_dict = self.handle_morphology(soup)
        chunk["morphology"] = cattrs.structure(morph_dict, PerseusMorphology)

    def _process_reference_chunk(self, chunk, soup):
        """Process reference chunk with definitions."""
        refs_dict = self.handle_references(soup)
        blocks = self._process_definition_blocks(refs_dict.get("blocks", []))
        chunk["definitions"] = DiogenesDefinitionEntry(
            term=refs_dict.get("term", ""), blocks=blocks
        )

    def _process_definition_blocks(self, blocks_data):
        """Process definition blocks from reference data."""
        blocks = []
        for b in blocks_data:
            if isinstance(b, DiogenesDefinitionBlock):
                blocks.append(b)
            elif isinstance(b, dict):
                blocks.append(self._create_definition_block_from_dict(b))
            else:
                try:
                    block_obj = cattrs.structure(b, DiogenesDefinitionBlock)
                    blocks.append(block_obj)
                except Exception as e:
                    logger.warning(
                        "Failed to structure block",
                        error=str(e),
                        block_keys=list(b.keys()) if isinstance(b, dict) else "not_dict",
                    )
                    blocks.append(self._create_basic_block(b))
        return blocks

    def _create_definition_block_from_dict(self, b):
        """Create definition block from dictionary data."""
        return DiogenesDefinitionBlock(
            entry=b.get("entry", ""),
            entryid=b.get("entryid", ""),
            citations=b.get("citations"),
            # senses=b.get("senses"),
            heading=b.get("heading"),
            diogenes_warning=b.get("diogenes_warning"),
        )

    def _create_basic_block(self, b):
        """Create basic definition block from fallback data."""
        return DiogenesDefinitionBlock(
            entry=b.get("entry", "") if isinstance(b, dict) else "",
            entryid=b.get("entryid", "") if isinstance(b, dict) else "",
            # senses=b.get("senses") if isinstance(b, dict) else None,
            citations=b.get("citations") if isinstance(b, dict) else None,
            heading=b.get("heading") if isinstance(b, dict) else None,
            diogenes_warning=b.get("diogenes_warning") if isinstance(b, dict) else None,
        )

    def _determine_chunk_type(
        self,
        is_perseus_analysis: bool,
        looks_like_header: bool,
        looks_like_reference: bool,
        dg_parsed: bool,
        is_fuzzy_match: bool = False,
    ) -> str:
        if is_perseus_analysis:
            return DiogenesChunkType.PerseusAnalysisHeader
        if looks_like_header:
            return DiogenesChunkType.NoMatchFoundHeader
        if looks_like_reference:
            if is_fuzzy_match:
                return DiogenesChunkType.DiogenesFuzzyReference
            return (
                DiogenesChunkType.DiogenesMatchingReference
                if dg_parsed
                else DiogenesChunkType.DiogenesFuzzyReference
            )
        return DiogenesChunkType.UnknownChunkType

    def get_next_chunk(self, result: ParseResultDraft, soup: BeautifulSoup) -> ChunkDraft:
        chunk: ChunkDraft = {"soup": soup}

        looks_like_header = False
        is_perseus_analysis = False
        looks_like_reference = False

        type_unknown = True

        for tag in soup.find_all("h1"):
            if tag.get_text().strip().startswith("Perseus an"):
                is_perseus_analysis = True
                type_unknown = False
                break

        for tag in soup.find_all(class_="logeion-link"):
            looks_like_header = True
            type_unknown = False
            onclick: str = str(tag.attrs.get("onclick", ""))
            parts = onclick.split("', 'Logeion', '")
            chunk["logeion"] = parts[0][13:]
            break

        if type_unknown:
            for tag in soup.find_all("a"):
                onclick: str = str(tag.attrs.get("onclick", ""))
                if onclick.startswith("prevEntry"):
                    pattern = r"\((\d+)\)"
                    match = re.search(pattern, onclick)
                    if match:
                        extracted_id = match.group(1)
                        chunk["reference_id"] = extracted_id
                        looks_like_reference = True
                        # Check if this is a fuzzy match (nearest entry)
                        chunk["is_fuzzy_match"] = result.get("is_fuzzy_overall", False)
                        break

        chunk_type = self._determine_chunk_type(
            is_perseus_analysis,
            looks_like_header,
            looks_like_reference,
            result.get("dg_parsed", False),
            chunk.get("is_fuzzy_match", False),
        )
        chunk["chunk_type"] = chunk_type

        logger.debug("chunk_classified", chunk_type=chunk.get("chunk_type"))
        return chunk

    def parse_word(self, word: str, language: str = DiogenesLanguages.LATIN) -> DiogenesResultT:
        assert language in DiogenesLanguages.parse_langs, (
            f"Cannot parse unsupported diogenes language: [{language}]"
        )

        logger.debug("parse_word", word=word, language=language)

        response = requests.get(self.__diogenes_parse_url(word, language))

        result: ParseResultDraft = {"chunks": [], "dg_parsed": False}

        if response.status_code == HTTP_OK_STATUS:
            logger.debug(
                "parse_word_response",
                status_code=response.status_code,
                content_length=len(response.text),
            )
            result["dg_parsed"] = True  # Set dg_parsed early so chunk classification works
            # Check if this is a fuzzy match overall
            response_text_lower = response.text.lower()
            result["is_fuzzy_overall"] = (
                "could not find dictionary headword" in response_text_lower
                or "showing nearest entry" in response_text_lower
            )
            documents = response.text.split("<hr />")
            logger.debug("parse_word_documents", count=len(documents))
            chunk_types = []
            for doc in documents:
                soup = self._make_soup(doc)
                chunk = self.get_next_chunk(result, soup)
                chunk_types.append(chunk["chunk_type"])
                self.process_chunk(result, chunk)
            result["chunk_types"] = chunk_types
        else:
            logger.warning("diogenes_request_failed", status_code=response.status_code, word=word)

        logger.debug(
            "parse_word_completed",
            chunks_count=len(result["chunks"]),
            dg_parsed=result["dg_parsed"],
        )
        return DiogenesResultT(**result)
