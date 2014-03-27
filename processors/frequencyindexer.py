"""
frequencyindexer
"""

from collections import defaultdict

from lxml import etree

from lex.oed.resources.frequencyiterator import FrequencyIterator

XSLPI = etree.PI('xml-stylesheet',
                 'type="text/xsl" href="./chrome/xsl/index.xsl"')


def index_frequency_files(in_dir, out_file):
    entry_list = defaultdict(lambda: defaultdict(list))
    iterator = FrequencyIterator(in_dir=in_dir,
                                 message='Compiling index')
    for e in iterator.iterate():
        entry_list[e.letter][e.filename].append(e.label)

    doc = etree.Element('letters')
    doc.addprevious(XSLPI)

    for letter in sorted(entry_list.keys()):
        num_files = len(entry_list[letter].keys())
        num_entries = sum([len(entry_list[letter][f])
                           for f in entry_list[letter].keys()])
        letter_node = etree.SubElement(doc, 'letterSet',
                                       letter=letter,
                                       files=str(num_files),
                                       entries=str(num_entries),)

        for filename in sorted(entry_list[letter].keys()):
            fnode = etree.SubElement(letter_node, 'file',
                                     name=filename,
                                     letter=letter,
                                     entries=str(len(entry_list[letter][filename])))
            t1 = etree.SubElement(fnode, 'first')
            t1.text = entry_list[letter][filename][0]
            t2 = etree.SubElement(fnode, 'last')
            t2.text = entry_list[letter][filename][-1]

    with open(out_file, 'w') as filehandle:
        filehandle.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        filehandle.write(etree.tounicode(doc.getroottree(),
                                         pretty_print=True,))
