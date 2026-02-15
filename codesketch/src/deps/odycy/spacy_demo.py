import spacy

# Now it should find it in your site-packages
nlp = spacy.load("grc_odycy_joint_sm")

doc = nlp("μῆνιν ἄειδε θεὰ Πηληϊάδεω Ἀχιλῆος")
for token in doc:
    print(f"{token.text} -> {token.lemma_} ({token.pos_})")
