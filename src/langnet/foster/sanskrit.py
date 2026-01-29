from langnet.foster.enums import FosterCase, FosterGender, FosterNumber

FOSTER_SANSKRIT_CASES = {
    "1": FosterCase.NAMING,
    "2": FosterCase.CALLING,
    "3": FosterCase.RECEIVING,
    "4": FosterCase.POSSESSING,
    "5": FosterCase.TO_FOR,
    "6": FosterCase.BY_WITH_FROM_IN,
    "7": FosterCase.IN_WHERE,
    "8": FosterCase.OH,
}

FOSTER_SANSKRIT_GENDERS = {
    "m": FosterGender.MALE,
    "f": FosterGender.FEMALE,
    "n": FosterGender.NEUTER,
}

FOSTER_SANSKRIT_NUMBERS = {
    "sg": FosterNumber.SINGLE,
    "pl": FosterNumber.GROUP,
    "du": FosterNumber.PAIR,
}

# Detailed case documentation for Foster's "Job Description" methodology
FOSTER_CASE_DOCUMENTATION = {
    FosterCase.NAMING: {
        "latin_case": "Nominative",
        "sanskrit_case": "Prathama",
        "foster_logic": "The 'Who' or 'What'",
        "description": "The subject/agent of the sentence.",
        "example_usage": "Identifies the doer of the action or the main topic.",
    },
    FosterCase.CALLING: {
        "latin_case": "Accusative",
        "sanskrit_case": "Dvitiya",
        "foster_logic": "The 'What' (Directly)",
        "description": "The object receiving the action.",
        "example_usage": "Identifies the direct recipient of the verb's action.",
    },
    FosterCase.RECEIVING: {
        "latin_case": "Ablative/Instrumental",
        "sanskrit_case": "Tritiya",
        "foster_logic": "The 'By/With/Through'",
        "description": "The instrument used to do the job.",
        "example_usage": "Identifies tools, means, or instruments by which an action is performed.",
    },
    FosterCase.POSSESSING: {
        "latin_case": "Genitive",
        "sanskrit_case": "Shashti",
        "foster_logic": "The 'Of/Belonging to'",
        "description": "Connection or possession.",
        "example_usage": "Indicates possession, relationship, or source.",
    },
    FosterCase.TO_FOR: {
        "latin_case": "Dative",
        "sanskrit_case": "Chaturthi",
        "foster_logic": "The 'To/For'",
        "description": "The purpose or the recipient.",
        "example_usage": "Indicates the indirect object or beneficiary of an action.",
    },
    FosterCase.BY_WITH_FROM_IN: {
        "latin_case": "Ablative/Locative",
        "sanskrit_case": "Panchami",
        "foster_logic": "The 'From/Away'",
        "description": "The source or point of departure.",
        "example_usage": "Indicates separation, source, or motion away from something.",
    },
    FosterCase.IN_WHERE: {
        "latin_case": "Ablative/Locative",
        "sanskrit_case": "Saptami",
        "foster_logic": "The 'In/At/On'",
        "description": "The location (time or place).",
        "example_usage": "Indicates location in space or time.",
    },
    FosterCase.OH: {
        "latin_case": "Vocative",
        "sanskrit_case": "Sambodhana",
        "foster_logic": "The Address",
        "description": "Direct address or calling.",
        "example_usage": "Used when directly addressing someone or something.",
    },
}

# Complete case mapping table for easy reference
FOSTER_CASE_MAPPING_TABLE = [
    {
        "foster_logic": "The 'Who' or 'What'",
        "latin_case": "Nominative",
        "sanskrit_case": "Prathama",
        "description": "The subject/agent of the sentence.",
    },
    {
        "foster_logic": "The 'What' (Directly)",
        "latin_case": "Accusative",
        "sanskrit_case": "Dvitiya",
        "description": "The object receiving the action.",
    },
    {
        "foster_logic": "The 'By/With/Through'",
        "latin_case": "Ablative/Instrumental",
        "sanskrit_case": "Tritiya",
        "description": "The instrument used to do the job.",
    },
    {
        "foster_logic": "The 'To/For'",
        "latin_case": "Dative",
        "sanskrit_case": "Chaturthi",
        "description": "The purpose or the recipient.",
    },
    {
        "foster_logic": "The 'From/Away'",
        "latin_case": "Ablative",
        "sanskrit_case": "Panchami",
        "description": "The source or point of departure.",
    },
    {
        "foster_logic": "The 'Of/Belonging to'",
        "latin_case": "Genitive",
        "sanskrit_case": "Shashti",
        "description": "Connection or possession.",
    },
    {
        "foster_logic": "The 'In/At/On'",
        "latin_case": "Ablative/Locative",
        "sanskrit_case": "Saptami",
        "description": "The location (time or place).",
    },
]
