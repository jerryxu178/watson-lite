import os
import wikipedia
import nltk
from nltk.tag.stanford import StanfordNERTagger
import re

# set the environment path in order to use the NER tagger
java_path = "C:/Program Files/Java/jdk1.8.0_131/bin/java.exe"
os.environ['JAVA_HOME'] = java_path
st = StanfordNERTagger('stanford-ner/classifiers/english.all.3class.distsim.crf.ser.gz',
					   'stanford-ner/stanford-ner.jar',
					   encoding='utf-8')

def search_wikipedia(answer_type, keywords, proper_nouns):
	"""
	For each proper noun from the question, look up the corresponding Wikipedia
	article. Look for potential answers in each article that have the correct
	POS tag depending on the question, and prioritize answers that are in 
	sentences containing keywords

	Returns a list of (answer, score) tuples
	"""
	wiki_pages = []
	for noun in proper_nouns:
		try:
			wiki_pages.append(wikipedia.page(noun))
		except:
			continue
	answers = []
	for page in wiki_pages:
		answers += process_page(answer_type, keywords, page)
	return answers

def generate_NE_dict(answer_type, keywords, page):
	"""
	Create a dictionary of named entities (proper nouns), with the entity as
	the key and the corresponding POS tag as the value
	"""
	NE_dict = {}
	contents = convert_unicode(page.content)
	NER_tagged_page = st.tag(nltk.word_tokenize(contents))
	curr_entity = "" 
	curr_tag = ""
	for elt in NER_tagged_page:
		if elt[1] != 'O':
			curr_entity += " " + elt[0]
			curr_tag = elt[1]
		else:
			if curr_entity != "":	
				NE_dict[str(curr_entity.strip())] = str(curr_tag)
				curr_entity = ""
				curr_tag = ""
	if curr_entity != "":
		NE_dict[str(curr_entity.strip())] = str(curr_tag)
	dates_dict = tag_dates(contents)
	NE_dict.update(dates_dict)
	return NE_dict

def convert_unicode(contents):
	"""
	Convert wikipedia page contents from unicode to ascii and also remove
	unwanted characters
	"""
	contents = contents.encode('ascii', 'ignore')
	contents = contents.replace("\n", "")
	contents = contents.replace("=", "")
	return contents

def contains(word, wordlist):
	"""
	Return True if the word or something similar to the word is in the word 
	list, and False otherwise
	"""
	return word in wordlist or word+"s" in wordlist or word[:-1] in wordlist

def process_page(answer_type, keywords, page):
	"""
	Retrieve and score all potential answers from the text

	Words in the text that have the correct POS tag pertaining to the question 
	are considered to be potential answers. Answers are scored based on the 
	number of keywords that are also found in the same sentence
	"""
	NE_dict = generate_NE_dict(answer_type, keywords, page)
	sentences = []
	encountered_NE = []
	for NE in NE_dict:
		if NE_dict[NE] == answer_type or answer_type == "ANY":
			contents = convert_unicode(page.content)
			sentences += [s + '.' for s in (contents).split('.') if NE in s]
			encountered_NE.append(NE)
	sentences = list(set(sentences))
	scored_answers = []
	for sent in sentences:
		score = 0
		for word in keywords:
			sentence_words = nltk.word_tokenize(sent.lower())
			if contains(word[0], sentence_words):
				score += 1
		for NE in encountered_NE:
			if NE in sent:
				scored_answers.append((NE, score))
	return scored_answers

def tag_dates(text):
	"""
	Look for all dates in the text, and return them in a dictionary where key
	is the date and value is "DATE"

	TODO: refactor duplicated code
	"""
	temp_text = text
	dates = [] # list of dates in text that require tagging
	dates_dict = {}
	dates += re.findall(r'[ADFJMNOS]+[a-z]* [0-3]?[0-9], [1-2][0-9]{3}', temp_text) # look for August 20, 1990
	temp_text = remove_dates(temp_text, dates)
	dates += re.findall(r'[ADFJMNOS]+[a-z]* [0-3]?[0-9] [1-2][0-9]{3}?', temp_text) # look for August 20 1990
	temp_text = remove_dates(temp_text, dates)
	dates += re.findall(r'[0-3]?[0-9] [ADFJMNOS]+[a-z]* [1-2][0-9]{3}?', temp_text) # look for 20 August 1990
	temp_text = remove_dates(temp_text, dates)
	dates += re.findall(r'[ADFJMNOS]+[a-z]* [1-2][0-9]{3}?', temp_text) # look for August 1990
	temp_text = remove_dates(temp_text, dates)
	dates += re.findall(r'[ADFJMNOS]+[a-z]* [0-3]?[0-9] ', temp_text) # look for August 20
	temp_text = remove_dates(temp_text, dates)
	dates += re.findall(r'[0-1]?[0-9]/[0-3]?[0-9]/[1-2][0-9]{3}', temp_text) # look for 8/20/1990
	temp_text = remove_dates(temp_text, dates)
	dates += re.findall(r'[1-2][0-9]{3}', temp_text) # look for 1990
	temp_text = remove_dates(temp_text, dates)
	for date in dates:
		dates_dict[date] = "DATE"
	return dates_dict

def remove_dates(text, dates):
	# remove dates in list from the text in order to avoid double tagging
	clean_text = text
	for date in dates:
		clean_text = clean_text.replace(date, "")
	return clean_text
