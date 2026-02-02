import re
from collections import defaultdict
from dataclasses import dataclass, field
from string import digits
from typing import Any

import betacode.conv
import cattrs
import requests
import structlog
from bs4 import BeautifulSoup

import langnet.logging  # noqa: F401 - ensures logging is configured before use

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
    senses: list[str] | None = field(default=None)
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

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url

        if self.base_url is None:
            self.base_url = "http://localhost:8888/"

        if not self.base_url.endswith("/"):
            self.base_url += "/"

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

    def _parse_perseus_morph(self, tag) -> dict:
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

        morph = dict(stem=cleaned_stems, tags=cleaned_tags)
        if cleaned_defs:
            morph["defs"] = cleaned_defs
        return morph

    def handle_morphology(self, soup: BeautifulSoup):
        morphs = []
        maybe_morph_els = []
        warning = None
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

        morph_dict: dict[str, Any] = dict(morphs=morphs)

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

    def _collect_senses(self, soup: BeautifulSoup) -> list[str]:
        senses = []
        for b in soup.select("b"):
            sense_txt = b.get_text().strip().rstrip(",").rstrip(":")
            if "(" in sense_txt and ")" not in sense_txt:
                sense_txt += ")"
            senses.append(sense_txt)
        return senses

    def _deduplicate_senses(self, senses: list[str]) -> list[str]:
        unique = []
        for sense in senses:
            if sense not in unique:
                unique.append(sense)
        return unique

    def _process_block(self, block: dict, soup: BeautifulSoup, indent_history: list):
        for p in soup.select("p"):
            _nothing, warning = self.extract_parentheses_text(p.get_text())
            block["diogenes_warning"] = warning.replace("\n", " ")
            p.decompose()

        refs = {}
        for ref in soup.select(".origjump"):
            ref_id = " ".join(ref.attrs.get("class", [])).strip("origjump ").lower()
            ref_txt = ref.get_text()
            refs[ref_id] = ref_txt
        if len(refs.items()) > 0:
            # converted_citations = []
            # for urn, citation_text in refs.items():
            block["citations"] = refs
            # CitationCollection(citations=converted_citations)
            logger.debug("handle_references_citations", count=len(refs))

        senses = self._collect_senses(soup)
        senses_cleaned = self._deduplicate_senses(senses)
        if len(senses_cleaned) > 0:
            block["senses"] = senses_cleaned

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
            block_copy = BeautifulSoup(f"{block}", "html5lib")
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

    def process_chunk(self, result, chunk):
        soup: BeautifulSoup = chunk["soup"]
        chunk_type: str = chunk["chunk_type"]

        logger.debug("process_chunk", chunk_type=chunk_type)

        if chunk_type == DiogenesChunkType.PerseusAnalysisHeader:
            morph_dict = self.handle_morphology(soup)
            chunk["morphology"] = cattrs.structure(morph_dict, PerseusMorphology)

        elif chunk_type in {
            DiogenesChunkType.DiogenesMatchingReference,
            DiogenesChunkType.DiogenesFuzzyReference,
        }:
            refs_dict = self.handle_references(soup)
            blocks = []
            for b in refs_dict.get("blocks", []):
                if isinstance(b, DiogenesDefinitionBlock):
                    blocks.append(b)
                elif isinstance(b, dict):
                    blocks.append(
                        DiogenesDefinitionBlock(
                            entry=b.get("entry", ""),
                            entryid=b.get("entryid", ""),
                            citations=b.get("citations"),
                            senses=b.get("senses"),
                            heading=b.get("heading"),
                            diogenes_warning=b.get("diogenes_warning"),
                        )
                    )
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
                        # Create a basic block with available data
                        basic_block = DiogenesDefinitionBlock(
                            entry=b.get("entry", "") if isinstance(b, dict) else "",
                            entryid=b.get("entryid", "") if isinstance(b, dict) else "",
                            senses=b.get("senses") if isinstance(b, dict) else None,
                            citations=b.get("citations") if isinstance(b, dict) else None,
                            heading=b.get("heading") if isinstance(b, dict) else None,
                            diogenes_warning=b.get("diogenes_warning")
                            if isinstance(b, dict)
                            else None,
                        )
                        blocks.append(basic_block)

            chunk["definitions"] = DiogenesDefinitionEntry(
                term=refs_dict.get("term", ""), blocks=blocks
            )
        else:
            logger.debug("process_chunk_unknown_type", chunk_type=chunk_type)
            pass

        del chunk["soup"]

        if chunk_type == DiogenesChunkType.PerseusAnalysisHeader:
            result["chunks"].append(PerseusAnalysisHeader(**chunk))
        elif chunk_type == DiogenesChunkType.NoMatchFoundHeader:
            result["chunks"].append(NoMatchFoundHeader(**chunk))
        elif chunk_type == DiogenesChunkType.DiogenesMatchingReference:
            result["chunks"].append(DiogenesMatchingReference(**chunk))
        elif chunk_type == DiogenesChunkType.DiogenesFuzzyReference:
            result["chunks"].append(DiogenesFuzzyReference(**chunk))
        else:
            soup_str = str(soup)
            logger.debug("process_chunk_unknown_appending", soup_preview=soup_str[:100])
            result["chunks"].append(UnknownChunkType(soup=soup_str))

    def _determine_chunk_type(
        self,
        is_perseus_analysis: bool,
        looks_like_header: bool,
        looks_like_reference: bool,
        dg_parsed: bool,
    ) -> str:
        if is_perseus_analysis:
            return DiogenesChunkType.PerseusAnalysisHeader
        if looks_like_header:
            return DiogenesChunkType.NoMatchFoundHeader
        if looks_like_reference:
            return (
                DiogenesChunkType.DiogenesMatchingReference
                if dg_parsed
                else DiogenesChunkType.DiogenesFuzzyReference
            )
        return DiogenesChunkType.UnknownChunkType

    def get_next_chunk(self, result: dict, soup: BeautifulSoup) -> dict:
        chunk: dict[str, Any] = {"soup": soup}

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
                        break

        chunk_type = self._determine_chunk_type(
            is_perseus_analysis,
            looks_like_header,
            looks_like_reference,
            result.get("dg_parsed", False),
        )
        chunk["chunk_type"] = chunk_type
        result["dg_parsed"] = chunk_type == DiogenesChunkType.PerseusAnalysisHeader

        logger.debug("chunk_classified", chunk_type=chunk.get("chunk_type"))
        return chunk

    def parse_word(self, word, language: str = DiogenesLanguages.LATIN) -> DiogenesResultT:
        assert language in DiogenesLanguages.parse_langs, (
            f"Cannot parse unsupported diogenes language: [{language}]"
        )

        logger.debug("parse_word", word=word, language=language)

        response = requests.get(self.__diogenes_parse_url(word, language))

        result: dict[str, Any] = dict(chunks=[], dg_parsed=False)

        if response.status_code == HTTP_OK_STATUS:
            logger.debug(
                "parse_word_response",
                status_code=response.status_code,
                content_length=len(response.text),
            )
            documents = response.text.split("<hr />")
            logger.debug("parse_word_documents", count=len(documents))
            for doc in documents:
                soup = BeautifulSoup(doc, "html5lib")
                chunk = self.get_next_chunk(result, soup)
                self.process_chunk(result, chunk)
            result["dg_parsed"] = True
        else:
            logger.warning("diogenes_request_failed", status_code=response.status_code, word=word)

        logger.debug(
            "parse_word_completed",
            chunks_count=len(result["chunks"]),
            dg_parsed=result["dg_parsed"],
        )
        return DiogenesResultT(**result)
