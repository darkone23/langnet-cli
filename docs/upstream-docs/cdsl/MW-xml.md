from: https://www.sanskrit-lexicon.uni-koeln.de/talkMay2008/mwtags.html

Current markup of Monier Williams Sanskrit-English Dictionary

This document describes the current markup of the Monier Williams Sanskrit-English Dictionary at the University of Cologne, as of April 2008.
Outline

General Structure
Structure common to each record
  root elements <H1> <H1A> <H1B> <H2> <H2A> <H2B> <H3> <H3A> <H3B> <H4> <H4A> <H4B> <HPW>
  root children <h> <body> <tail>
The head section
  <hc3>   <key1>   <hc1>
  <key2>    ( special chars   <TWOWORDS/>   <sr/> <sr1/>   <srs/> <srs1/>   <shortlong/>   <root> )
  <hom>
The body section
  marking special characters ( <b> <b1>   <p> <p1>   <c> <c1> <c2><c3>   <quote>   <sr/> <sr1/>   <fcom/>   <abE/>   <srs/> <srs1/>   <shortlong/> <shc/>   <auml/> <euml/> <ouml/> <uuml/>   <etc/> <etc1/> <etcetc/>   <amp/>   <eq/>   <fs/>   <msc/>   <ccom/> )
  marking special text ( <ab>   <etym>   <s>   <as0> <asp0> <as1>   <ns>   <bot> <bio>   <root> and <root/>   <to/>   <ls>   <lex>   <vlex>   <hom>   <pc> <pcol>   <phw>   <ORSL> )
  experimental marking ( <usage> <idiom> <sense> <ellipsis/>   <loan/> )

  marking references to other records ( <cf/>   <qv/>   <see/>   <pL> <dL>   <AND/> <OR/> )
The tail section ( <L>   <pc>   <MW>   <mul/>   <mat/>   <mscverb/> )
General Structure

The dictionary appears as a sequence of 280081 records. Each record is coded as a text string (using the standard ASCII 7-bit character set) which has a well-formed XML structure. A Perl program (mwtab_wf.pl) is used periodically to check that each record is well-formed. Dictionary entries for verbs correspond to records. Dictionary entries for non-verbs correspond to record sequences, with each record corresponding to a sense of the entry. The ordering of records corresponds to the dictionary ordering and is maintained by an element <L> whose content is a numerical identifier.
From an examination of global statistics on frequency of element occurence, one notes that 103 element-attribute variations occur; there are on average about 17 elements per record.

There is no DTD against which to determine the validity of the XML structure. However, there are regularities to the markup. Most of the following remarks are aimed at describing these regularities.
Structure common to each record

Each record has an overall form using one of 13 'H' root elements and a set of 9 other elements.
The 13 root elements are

    <H1> <H1A> <H1B> <H2> <H2A> <H2B> <H3> <H3A> <H3B> <H4> <H4A> <H4B> <HPW> . 

The 9 common elements appearing in each record are

    root children: <h> <body> <tail>
    children of <h> : <hc1> <hc3> <key1> <key2>
    children of <tail> : <L> <pc> 


As a basis of discussion, consider the first record of the coded dictionary:

    <H1><h><hc3>000</hc3><key1>a</key1><hc1>1</hc1><key2>a</key2><hom>1</hom></h><body> <c>the_first_letter_of_the_alphabet</c> </body><tail><pc>Page1,1</pc> <L>1</L></tail></H1> 

root elements
One of the 'H' elements forms the root element. There are four basic H elements, named H1,H2,H3,H4; these are intended to correspond to the 'four mutually correlated lines of Sanskrit words' described at Page xiv: Section II of the dictionary preface. These were coded in MONIER.ALL based upon the delineating typographic features of the text.
For non-verbs with multiple senses, these four basic elements are further refined by a suffix 'A' or 'B'. 'A' means that the speficic lexical information (e.g., masculine, feminine, neuter) is the same as that of the preceding 'parent' entry; 'B' means that the specific lexical information differs from that of the 'parent'. Currently there is no pointer from an 'A' or 'B' child to its parent; the relation is implicit in the ordering of the records, but an explicit coding of this relation should probably be done.
For instance, the second record of the dictionary provides an alternate sense to the first record shown above, and is coded with root element 'H1A':

    <H1A><h><hc3>000</hc3><key1>a</key1><hc1>1</hc1><key2>a</key2><hom>1</hom></h><body> <c>the_first_short_vowel_inherent_in_consonants.</c> </body><tail><pc>Page1,1</pc> <MW>000001</MW> <L>1.1</L></tail></H1A> 


Currently, the different 'parts' of a record for a verb are not separated into separate records, but are distinguished by an empty element <msc/> (coded in MONIER.ALL as '{;}') because the dictionary generally uses a semicolon for this separation (but semicolons are appear elsewhere , so this is a special semicolon).
There is a fifth form, 'HPW', which the root element name may take. This was devised to allow a separate records for 'parenthetical head words', discussed further below
One could imagine a different coding of the information of the 13 'H' elements in which there would be a single 'H' element with an attribute having 13 different value; e.g., <H type='1'> instead of <H1>.

root children

The children of the root element are the <h> <body> <tail> elements, in that order. The <h> (or 'head') element contains information about the head word. The <body> contains the definitional material of the record. The <tail> contains record sequencing information and a pointer to the scanned image of the pages of the dictionary.
The head section

The <h> element contains the elements <hc3> <key1> <hc1> <key2> and optionally <hom> , in that order.

    <hc3> : a 3-digit code, assigned in MONIER.ALL as a classification of the form of records. These are not particularly reliable in the current version of the dictionary.
    <key1> : This element contains the headword of the record. As with all other identified Sanskrit in the current coding of the dictionary, the Sanskrit of the headword is coded using the SLP1 transliteration scheme of Scharf. MONIER.ALL consistently uses the Harvard-Kyoto transliteration scheme in MONIER.ALL and in digitizations of other Sanskrit. Software is available to convert among various transliterations. key1 is used for 'citation' when using display programs to look up a word.
    <hc1> : This is a vestigial element carried over from MONIER.ALL.
    <key2> : Many of the entries in the dictionary have information about the head word in addition to the sequence of letters. This additional information is encoded into key2 using a few characters that do not appear in key1 and a few XML elements. The value of key1 is deriveable from key2 by removing the special charactars and xml elements. The special characters and elements that appear within key2 are as follows:
        - : separates compound word components. Two dashes are used in H3 records, e.g., /aMsa--tra. Three dashes are used in H4 records, e.g. /aMsa--tra---koSa.
        / : SLP1 representation of an udAtta accent which appears in the text as a forward sloping linear mark above the vowel. There is currently no distinguished coding of the much less frequent backward-sloping accent mark (svarita accent) (as in atitAry/a where note the accent is marked also with /), or of the even less frequent occurence of both accent marks.
        ' : The apostrophe in SLP1 represents avagraha. This currently appears in 199 records, for example ato-'nya, meaning 'differing from this.'
        space : the blank or space character appears in a few (about 70) records, such as 'aTa ced' (meaning 'but if') and 'dIrG/a--tama<sr1/>so vrata' (name of a saman).
        <TWOWORDS/> : An experimental coding for a headword composed of more than one word. Currently only appears once: 'sAma--ga---gAnAM<TWOWORDS/>Candas'.
        <sr/> : Used in examples such as 'gANga<sr/>waka' where the head word is only partially expressed in the text. In the example, he text shows three head words as 'gANga/wa, <sr/>waka, <sr/>weya', and the <sr/> represents a small superscript circle in the text.
        <sr1/> : I think this is semantically equivalent to <sr/> . Probably not both elements are required.
        <srs/> : single replacement sandhi; placed immediately after the vowel (A, I, U, e, o). This marking often occurs in place of the '-' in compound head words.
        <srs1/> : single replacement sandhi; placed immediately after the vowel (E, O). Probably could code this also as <srs/>.
        <shortlong/> : A few (58 currently noted) words have alternative spellings where a particular vowel may be either short or long, for example 'ararA<shortlong/>kA'. In these cases, separate records for the two spellings have been created, with a bit of additional coding in the <body> element.
        <root> : This is used to specify the verbal root in prefixed verbs, for instance 'ati-<root>kfz</root>'. This element also appears for the same purpose for those prefixed verbs for which the spelling is altered in the key due to sandhi.
    <hom> : Some words with the same spelling appear in multiple entries in the dictionary, and are distinguished in the text by a digit. If present, this digit appears as the content of the <hom> element in the head of a record. This number also sometimes appears within the 'body' section of a record for another word, in order to refer to a particular homonym of the referenced word. Some of these latter homonym numbers are also marked by a <hom> element, but this marking is incomplete.

The body section

Except for the headword information of the <h> element and the sequencing information of the <tail> element, the dictionary text appears within the <body> element of the records. The multiplicity of forms of this text has thus far resisted efforts at fitting into a useful DTD, although one could describe a complex XML structure to which the markup would conform. In general, any element can be a child of any other within the <body>, and the elements can appear in any order.
marking special characters

Some elements mark individual characters

    <b> <b1> : These elements mark material appearing within square brackets '[]' in the text. For instance '<b>this is bracketed text</b>' is the marking of '[this is bracketed text]'. The <b1> has the same meaning, and is used in the few instances where bracketed text appears within bracketed text; for instance '<b>this is <b1>more</b1> bracketed text</b>' is the marking of '[this is [more] bracketed text]'. The consistent use of <b1> in addition to <b> permits regular expression searches to accurately select bracketed text; otherwise a more complicated iterative process must be used. This was the initial thinking that dictated the use of <b1>. While useful in the initial conversion of MONIER.ALL to an XML structure, the marking of levels of brackets is more annoying than useful when working with the already marked data.
    <p> <p1> : These elements mark material appearing within parentheses '()' in the text, in the same way that <b> and <b1> mark bracketed material.
    <c> <c1> <c2> <c3> _ ~ : MONIER.ALL was modified from a simpler digitization using a particular text editor, Kedit. In this modification, it was apparently found useful to identify sequences of text that belonged together. This was done by using particular extended Ascii codes to begin and end the text sequence, and one of two particular codes to indicate the white space appearing in the sequence. In the XML coding, the beginning and ending codes are replaced by the opening and closing <c> element, and the white space characters by the '_' and '~' characters, which otherwise do not appear within the text. The use of <c1> etc. indicates nested chunks. These odd marking conventions were required to permit conversion back to the original form of MONIER.ALL. For a user of the XML version of the dictionary, they are probably best omitted (change _ and ~ to a single space, delete <c> , </c>, etc.)
    <quote> : used to mark quoted text.
    <sr/> <sr1/> : represents, within Sanskrit text, the small superscript circle used within the dictionary to represent omitted characters. This one of the numerous abbreviation techniques used in the dictionary.
    <fcom/> : represents, within non-Sanskrit, non-English text, a small superscript circle. Rare; significance unclear.
    <abE> : This non-empty element represents the small superscript circle used with abbreviated English in the text. Typically, the letters of the abbreviation are the element contents, and the subsequent text is the un-abbreviated text. For example '<abE>h</abE>hard' or '<abE>h</abE>hundred'. This element also occurs with abbreviated Anglicized Sanskrit. Often, it is difficult to determine the intended expansion of the abbreviation, and the user should recognize that the expansion does not appear within the dictionary text.
    <srs/> <srs1/> : represents, within Sanskrit text, the circumflex used within the dictionary to represent single replacement sandhi.
    <shortlong/> <shc/> : represents, within Sanskrit text, the superscript symbol (line below semi-circle) used above a vowel to indicate that the vowel may be either in short or long form. There is probably no need for two elements, and the <shc/> could be changed to <shortlong/>.
    <auml/> <euml/> <ouml/> <uuml/> : Represent the various umlaut characters. These could be coded as XML entities.
    <etc/> <etc1/> <etcetc/> : Represent various kinds of '&c.' ; some alternate representation, more normally by an XML entity, is required for XML correctness.
    <amp/> : Represents the '&' character.
    <eq/> : Represents '=' character which appears in definitions in the form 'word1 = word2'. This distinguishes such usages of '=' from others, such as in XML markup involving attributes.
    <fs/> : Represents '/' character which appears in the text as a separator between alternatives.
    <msc/> : Represents ';' when deemed to have a 'sense-separator' function. Occurs almost exclusively within records for verbs. There are other uses of the ';' character within the text, such as within long parenthetical material, which are not marked with the <msc/> element.
    <ccom/> : Represents a character in MONIER.ALL used to represent certain complex records that needed further attention. Currently, there are only about 100 instances; these elements are probably now vestigial and should be removed.

marking special text

Some text is special in one way or another. This includes Sanskrit text, abbreviated text, textual representations of words in other languages, technical text, grammatical text, referential text. This section describes the various schemes devised to mark some of these.

    <ab> : Marks abbreviations. In the preface to the dictionary there is a page with a list of a couple of hundred abbreviations. Most of these are marked with the <ab> element. For instance, <ab>cf.<./ab> means 'confer, compare.' We have also created an ancillary mySQL table with this information to facilitate its display in dictionary access programs.
    Some abbreviations mentioned in the dictionary preface have been marked in some other way. These include lexical specifications (m., ind., cl., P., etc.) and a few abbreviations (L., Cat.) which appear in the preface both in the list of abbreviations and in the list of works and authors.
    Two common abbreviations (q.v. and cf.) are also sometimes coded as empty elements (<qv/> and <cf/>). This was done in part because of the minor differences in spelling (e.g., Cf.) under which the abbreviations appear.
    There are many other abbreviations that have been noted (e.g., Imper., sg.) which appear in the text but not in the preface; some of these have been marked, but the process is incomplete.
    <etym> : Marks non-Sanskrit text that appears at the end of some dictionary entries. For instance, '<c><ab>Eng.</ab></c>~<etym>eight</etym>' in the entry for Sanskrit 'azwan' presumably indicates that the Sanskrit word is considered to be part of the etymology of the English word.
    Where the text presents the non-Sanskrit word in a non-Latin alphabet, as with Greek, the non-Sanskrit word is omitted and represented by the character '$'.
    An interesting project would elaborate the coding of the etymological section, including providing transliteration of Greek, to make this information more useful.
    <s> : Marks Sanskrit text; the text itself appears in the SLP1 transliteration, although it appears in the Harvard-Kyoto transliteration within MONIER.ALL.
    Several elements appear occasionally as child elements of an <s> element. The text is often a partial Sanskrit word, with the missing parts being indirectly indicated by use of the '-' or the emtpy elements <sr/> or <sr1/>. The empty elements <sr/> and <sr1/> represent vowels lengthened due to sandhi; the empty elements <shortlong/> and <shc/> indicate vowels which may be either short or long. The <root> element appears in the body of some records for prefixed verbs to indicate the citation form of the root. The empty element <root/> otherwise indicates that the following Sanskrit text is a root.
    There are also a very small number of occurrences within <s> elements of the bracket element <b> and the parenthesis elements <p> and <p1> ; probably these cases should be examined for felicity of coding.
    <as0> <asp0> <as1> : These elements code Sanskrit words which appear in the text in the 'indological' font; normally such words are also capitalized. Such words are coded in MONIER.ALL with a special Anglicized Sanskrit transliteration, but they are not otherwise marked. Most instances can be recognized by the presence of a digit within a capitalized word. In the XML marking, the Anglicized Sanskrit is marked with the <as0> element (or <asp0> for plurals) and also the corresponding SLP encoding of the Sanskrit appears in a following <as1> element. For instance, '<as0>Vishn2u</as0><as1><s>vizRu</s></as1>'; note that the SLP appears within the <s> element. Roughly 9000 Anglicized Sanskrit words occur in about 55000 instances in the dictionary.
    A slight variant of this coding is also used to represent 'Sanglish', or words coded with the Anglicized Sanskrit encoding which are part Sanskrit and part English. Consider the example '<as0 type="ns">Bra1hman</as0><as1>Brahman</as1>'; here the 'translation' is written without an enclosing <s>.
    A separate mySQL table has been constructed containing all these Anglicized Sanskrit words, along with transliteration and citation references to other dictionary words. It is desireable for a Sanskrit scholar to examine this list, with especial attention to the words classified as 'non-Sanskrit' via the 'type="ns" attribute, and also for a fairly small number of words which appear to be Sanskrit but for which citations in the dictionary have not been found.
    <ns> Rarely used (10 instances) coding of non-Sanskrit text. Possibly should be converted to '<as0 type="ns">'.
    <bot> <bio> Mark taxonomic designations for plants and animals. This marking has been done by a process of intellingent guesses. Usually words in a taxonomic designation appear capitlized in the text; so another reason for marking such words was the practical one of eliminating them as Anglicized Sanskrit words.
    It is hoped that someone with technical knowledge of botanical naming conventions can develop cross-references from the dictionary to standard taxonomic references, as this would make this specialized information much more useful to a user of the dictionary.
    <root> and <root/> Mark Sanskrit roots. The empty element precedes the root, as in '<root/>~<s>pUR</s>'.
    <to/> : Flags the next word 'to' as being part of an infinitive form. Current utility unclear.
    <ls> Marks literary sources. There are about 300000 such markings, more than 1 per record, on average. A literary source typically appears as an abbreviation coded in Anglicized Sanskrit. There is a two-page list of Works and Authors in the dictionary preface which gives the abbreviation and corresponding unabbreviated form for most, but not all, of the abbreviations appearing in the text.
    Several ancillary files have been developed for the literary sources.
        MWWorksAuthors : an XML file based on the list of works and authors in the preface of the dictionary.
        mw-authorities.rng : relax NG description of MWWorksAuthors
        mw-authorities.rnc : compact relax NG description of MWWorksAuthors
        linktab : Provides the association between the Anglicized Sanskrit abbreviations and the entries in MWWorksAuthorsCurrentMarkup3.xml.

    Currently about 900 (0.3%) of the abbreviated works remain unexplained. For instance, the abbreviations 'PBr.'(141 times), 'Devi1P.' (39), 'Tantr.' (37), and 'Kr2ishn2aj.' (31) are unresolved. Resolution requires assistance from someone with knowledge of Sanskrit literature.
    There are many instances in the dictionary where references to works are given in an abbreviated form in which the work itself is not mentioned; presumably these are resolvable into complete references based upon a previous reference. An improved coding might resolve the missing work.
    It is interesting to contemplate linking references to digitized editions of the text. For instance, there are 5000 specific references to the Mahabharata, and there is a digitized critical edition of this work. However, the references in the dictionary are to editions (primarily Calcutta and Bombay editions), and there is no available way to correlate the references to the digitized edition.
    <lex> : Contains grammatical information for substantives and indeclineables. For substantives, this information is usually just the gender or genders in which the noun or adjective is inflected. Sometimes there is additional information, such as an indication of how the feminine stem is formed or whether the word appears only at the end of compounds.
    The <lex> element coding has been enhanced with a 'type' attribute. This enhancement was motivated by the goal of extracting from the dictionary an ancillary lexical grammar table, which would provide the basis for generating inflections for all the nominal forms in the dictionary. Such a table of inflected forms, with appropriate links back to the dictionary, appears essential to the goal of computer-assisted textual analysis.
    There follows a listing of the values of the 'type' attribute of the <lex> element.
        <lex> : The absence of an attribute is by far the most common instance, roughly 193000 of these occur. The interpretation is that the content of the <lex> element provides inflectional information for the headword of the record as it appears in the dictionary.
        <lex type="inh"> : The 'inheritance' attribute means that the content of the element is inherited from the previous record with an untyped <lex> for the given head word. This occurs for about 64000 records. For nominals with many senses, the dictionary typically does not repeat inflectional information for different senses. Rather than following the text in such cases, the coding repeats the 'implied' lexical information, and marks the repetition with the 'inh' attribute.
        <lex type="hw"> : For some (about 1500) records, the inflectional information is spread through the record. In these cases, the first inflectional information for the head word appears within an untyped <lex>, and subsequent inflectional information for the head word appears with the 'hw' type.
        <lex type="hwalt"> : This is similar to the 'hw' attribute value in that it contains additional inflectional information for the head word, but differs in that the information appears to be an alternative to the main inflectional information.
        <lex type="hwifc"> : This marks cases where the inflectional information is relevant to the head word when the head word appears at the end of a compound. It is signalled by the presence of the 'ifc.' abbreviation.
        <lex type="hwinfo"> : This marks cases where the inflectional data pertains to the head word, but does not add new information relevant to inflection; for instance, it may indicate that a head word already known to be masculine has a certain meaning when used in the plural or a certain form when used in the locative case.
        <lex type="nhw"> : This indicates that the lexical information does not pertain to the head word. For instance, the meaning of the head word may be the same as masculine form of another word.
        <lex type="part"> : This designation typically appears in verb records where the feminine form of a participle is given.
        <lex type="phw"> : This indicates that the inflectional information is for a 'parenthetical head word'. It occurs only within the scope of a <phw> element.
    <vlex> : Marks inflectional information about verbs. Typically the contents are conjugational class and 'P' or 'A1'. As with the <lex> element, there is a 'type' attribute. The values 'hwalt', 'hwinfo', and 'nhw' have meanings analogous to the meanings for <lex>.
    There is no 'inh' value used currently with <vlex> because the records for verbs have not been split. Future coding may provide more refinement in the coding of types for verbs.
    There are two values of the 'type' attribute used only with <vlex>.
        <vlex type="root"> : Used as an empty element to designate the given record as that for a root verb. Currently, 1837 records are so marked.
        <vlex type="preverb"> : Used for prefixed verbs to contain the root and possibly prefixes, when this information is not implicitly given in <key2>. This occurs in about 600 records. However, there are almost 7000 records which are prefixed verbs; these are identified by the presence of a non-empty <root> element.
    <hom> : Marks a digit as refering to a particular variant of a word. For example, within the body of the record for the prefixed verb 'anuprAs', there appears '<vlex type="preverb"><hom>2</hom> <s><root>as</root></s></vlex>' which tells us that the 2nd variant of the root 'as' (meaning 'to throw') is intended.
    The coding of <hom> within the <body> is incomplete; currently only 114 instances are coded.
    <pc> <pcol> : <pc> within <body> indicates a transition in the text from one page and column to the next. <pcol> codes a reference in the text to another page and column of the text.
    <phw> : Codes an implicitly specified 'parenthetical head word'; a separate record is created with the implicit word as head word, and pointing back to the record with the implicit specification. Parenthetical head words is the term we use to refer to dictionary entries which are mentioned only within the definition of another head word; currently, only such instances are coded which also have explicitly associated lexical information. This was done to facilitate the completeness of coverage of a Lexical Grammar Table for Scharf's aim of a full-form lexicon.An example should make the process clear.

        <H2A><h><hc3>100</hc3><key1>avakASa</key1><hc1>2</hc1><key2>ava-kAS/a</key2></h><body> <lex type="inh">m.</lex> <c>aperture</c> <ls>Sus3r.</ls> <p><phw><dL>516974</dL><s><sr1/>Sena</s>~ <ab>instr.</ab>~ <lex type="phw">ind.</lex></phw>~<c>between</c>~<ls>PBr.</ls></p> </body><tail><pc>96,2</pc> <L>16974</L></tail></H2A>

        <HPW><h><hc3>600</hc3><key1>avakASena</key1><hc1>5</hc1><key2>ava-kASena</key2></h><body> <lex>ind.</lex> <pL>16974</pL> </body><tail><L>516974</L></tail></HPW> 


    The record for 'avakASa' implicitly specifies the indeclineable head word 'avakASena'; the <dL> element in 'avakASa' contains the 'L' identifier of the 'daughter' record for 'avakASena'. The record for 'avakASena' contains the lexical information and a pointer in the <dL> element back to the parent record. The 'L' identifier of the new head word is 500000 + 16974, so such records occur after all the 'regular' entries.
    There are currently 2407 daughter records.
    <ORSL> : Some dictionary entries have alternate spellings where a certain vowel can be either short or long. In these few (about 60) cases, two records are coded for each sense. In the parent record, the <ORSL> element contains the <dL> element pointing to the daughter record; and in the daughter record, the <ORSL> element contains the <pL> element pointing to the parent record. The following example shows this coding.

        <H1><h><hc3>004</hc3><key1>aBIpada</key1><hc1>1</hc1><key2>aBI-pa<shortlong/>da</key2></h><body> <ORSL><dL>13034.1</dL></ORSL> <see/> <c>1.</c> <s>a-BI</s>. </body><tail><mul/> <MW>009564</MW> <pc>74,3</pc> <L>13034</L></tail></H1>

        <H1><h><hc3>004</hc3><key1>aBIpAda</key1><hc1>1</hc1><key2>aBI-pA<shortlong/>da</key2></h><body> <ORSL><pL>13034</pL></ORSL> <see/> <c>1.</c> <s>a-BI</s>. </body><tail><mul/> <MW>009564</MW> <pc>74,3</pc> <L>13034.1</L></tail></H1> 

experimental marking

The following are experimental markings; there is only one instance of each in the current markup of the dictionary.

    <usage> <idiom> <sense> <ellipsis/>

        <H1><h><hc3>200</hc3><key1>aDa</key1><hc1>1</hc1><key2>/aDa</key2></h><body> <c>or</c> <s>/aDA</s> <lex>ind.</lex> , <c>Ved._<p><eq/>_<s>/aTa</s>_,_used_chiefly_as_an_inceptive_particle</p>_,_now_,_then_,_therefore_,_moreover_,_so_much_the_more_,_and_,_partly.</c> <usage><idiom><s>/aDa</s><ellipsis/><s>/aDa</s></idiom><sense><c>as_well_as_,_partly_partly.</c></sense></usage> </body><tail><MW>002776</MW> <pc>19,3</pc> <L>3951</L></tail></H1> 

    <loan/> This marking, occuring within the <h> element, could be used to mark the few 'loan words' which are dictionary entries.

        <H1><h><hc3>110</hc3><key1>sArisTAK~A</key1><hc1>1</hc1><key2>sArisTA-K~A</key2><loan/></h><body> <lex>m.</lex> <c>N._of_a_<as0 type="ns">Kha1n</as0><as1>Khan</as1></c> <ls>Kshiti7s3.</ls> </body><tail><mul/> <MW>152733</MW> <pc>1209,2</pc> <L>243121</L></tail></H1> 

marking references to other records

A small number of elements indicate references to other records or words.

    <cf/> : Confer. Sometimes refers to another word in dictionary; sometimes, to etymologies. Appears in text as 'c.f.' and is also coded as abbreviation c.f..
    <qv/> : quod vide ('which see'). Usually refers to another word in dictionary. Appears in text as 'q.v.' or 'qq.vv.', and is also coded as abbreviation q.v..
    <see/> : See. Usually refers to another word in dictionary. Appears in text as the word 'see'.
    <pL> <dL> : Parent L-number, daughter L-number. Provides links between records for <phw> and <shortlong/> constructed records.
    <AND/> <OR/> : Frequently in the text, multiple headwords are presented preceding one or more senses which presumably apply to any of the headwords; the last two head words in the sequence will typically be joined by the word 'and' or the word 'or'. Such cases were coded in a certain way in MONIER.ALL, and the current coding is the same.
    The method is illustrated by some sub-compounds of 'aMSa' appearing on page 1, column 1 of the text. A fairly literal rendering of the dictionary text is:

        -kalpanA, f. or -prakalpanA, f. or -pradAna, n. allotment of a portion. 

    This information is coded as three records, with the <OR/> empty element appear in all but the last record:

        <H3><h><hc3>110</hc3><key1>aMSakalpanA</key1><hc1>3</hc1><key2>/aMSa--kalpanA</key2></h><body> <lex>f.</lex> <OR/> <c>allotment_of_a_portion.</c> </body><tail><MW>000012</MW> <pc>1,1</pc> <L>21</L></tail></H3>

        <H3><h><hc3>110</hc3><key1>aMSaprakalpanA</key1><hc1>3</hc1><key2>/aMSa--prakalpanA</key2></h><body> <lex>f.</lex> <OR/> <c>allotment_of_a_portion.</c> </body><tail><MW>000013</MW> <pc>1,1</pc> <L>22</L></tail></H3>

        <H3><h><hc3>110</hc3><key1>aMSapradAna</key1><hc1>3</hc1><key2>/aMSa--pradAna</key2></h><body> <lex>n.</lex> <c>allotment_of_a_portion.</c> </body><tail><MW>000014</MW> <pc>1,1</pc> <L>23</L></tail></H3> 

    For a simple definition like this, the technique is acceptable, although one might question the technique of omitting the <OR/> flag for the last member.
    But this technique encounters several complications:
        1. Sometimes there are multiple senses, some of which may apply to only one alternative.
        2. Sometimes there are alternate forms or compounds, some of which may apply to only one alternative.
        3. There may be a large number of senses. One extreme example appears with the word 'Sakti' where the two alternatives differ only in the placement of accents (thus, they have the same 'key1' value), and there are 13 senses.
    Contemplating such examples might cause one to long for a simpler coding.
    The <AND/> and <OR/> elements occur in about 4000 records.

The tail section

The <tail> element of every record contains the <L> and <pc> elements; some records also variously contain <MW> , <mul/> , <mat/> and <mscverb/> elements. The ordering of these elements varies.

    <L> : an identifier containing a decimal number; its value equals the mySQL 'lnum' column which is declared as 'DECIMAL(10,2) UNIQUE'. A Perl program (mwtab_chklnum.pl) is used periodically to check that the text of the <L> element equals the 'lnum' column for each record.
    <pc> : contains a page and column number so that the the text of the <body> element for the record is digitized from text appearing in the given column of the given page of the dictionary. This facilitates cross-checking of the digitization with the textual basis of the digitization. Computer display programs of the record can provide a link to the scanned image of the page.
    Some records appear within more than one column of the text, and multiple <pc> elements are used in this case. Furthermore, following MONIER.ALL, the element is placed at the location within the record text at which the column break occurs.
    Due in part to the intentional splitting of MONIER.ALL records in the process of XML markup, there are still some inaccuracies in the values of this element, which should be corrected for the most part in a month or two.
    <MW> : entry containing a sequencing number in MONIER.ALL; has been superceded by <L> entry for purposes of record identification, but may have utility related to record grouping
    <mul/> : coding of a particular '_' character in MONIER.ALL; meaning unclear but possibly related to record grouping.
    <mat/> : coding of a particular '@' character in MONIER.ALL; meaning unclear but possibly related to record grouping.
    <mscverb/> : probably should be removed; originally inserted to identify records which were verbs with multiple parts separated by the <msc/> element.


