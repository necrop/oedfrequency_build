"""
FrequencyCollector - Collects frequency data for OED entries from GEL
"""

import os
import string
from collections import defaultdict, namedtuple

from lxml import etree

from lex.gel.dataiterator import OedContentIterator
from lex.entryiterator import EntryIterator
from lex.frequencytable import sum_frequency_tables

XSLPI = etree.PI('xml-stylesheet',
                 'type="text/xsl" href="../chrome/xsl/base.xsl"')
MAX_BUFFER = 2000  # entries per file
DEF_LENGTH = 50  # number of characters in definition

WordclassData = namedtuple('WordclassData', ['wordclass', 'frequency_table',
                                             'types'])
TypeData = namedtuple('TypeData', ['form', 'wordclass', 'frequency_table'])


class FrequencyCollector(object):

    def __init__(self, **kwargs):
        self.out_dir = kwargs.get('out_dir')
        self.terse = kwargs.get('terse', True)
        self.include_subentries = kwargs.get('include_subentries', False)
        self.frequencies = None
        self.filecount = None

    def process(self):
        for letter in string.ascii_lowercase:
            _clear_dir(self.out_dir, letter)
            frequencies, subfrequencies = _load_frequency_data(letter, self.include_subentries)

            print('Listing frequencies for entries in %s...' % letter)
            file_filter = 'oed_%s.xml' % letter.upper()
            iterator = EntryIterator(dictType='oed',
                                     fixLigatures=True,
                                     fileFilter=file_filter,
                                     verbosity=None)

            self.filecount = 0
            previous = None
            self.initialize_doc()
            for e in iterator.iterate():
                sortcode = e.lemma_manager().lexical_sort()

                if e.id in frequencies:
                    frequency_blocks = frequencies[e.id]
                else:
                    frequency_blocks = []
                enode = _construct_node(e, 'entry', e.id, 0, e.label(),
                                        e.label(), frequency_blocks, self.terse)
                self.doc.append(enode)

                if self.include_subentries:
                    for sense in e.senses():
                        sig = (e.id, sense.node_id())
                        if sig in subfrequencies:
                            frequency_blocks = subfrequencies[sig]
                            subnode = _construct_node(sense, 'subentry',
                                e.id, sense.node_id(), sense.lemma, e.label(),
                                frequency_blocks, self.terse)
                            self.doc.append(subnode)

                if self.buffersize() >= MAX_BUFFER and sortcode != previous:
                    self.write_buffer(letter)
                    self.initialize_doc()
                previous = sortcode
            self.write_buffer(letter)

    def write_buffer(self, letter):
        filepath = os.path.join(self.out_dir, letter, self.next_filename())
        with open(filepath, 'w') as filehandle:
            filehandle.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            filehandle.write(etree.tounicode(self.doc.getroottree(),
                                             pretty_print=True))

    def initialize_doc(self):
        self.doc = etree.Element('entries')
        self.doc.addprevious(XSLPI)

    def buffersize(self):
        return len(self.doc)

    def next_filename(self):
        self.filecount += 1
        return '%04d.xml' % self.filecount


def _clear_dir(directory, letter):
    sub_dir = os.path.join(directory, letter)
    if not os.path.isdir(sub_dir):
        os.mkdir(sub_dir)
    for filename in os.listdir(sub_dir):
        os.unlink(os.path.join(sub_dir, filename))


def _load_frequency_data(letter, include_subentries):
    frequencies = defaultdict(list)
    subfrequencies = defaultdict(list)
    iterator = OedContentIterator(letter=letter,
                                  include_entries=True,
                                  include_subentries=include_subentries)
    for wordclass_set in iterator.iterate():
        if wordclass_set.has_frequency_table():
            oed_id = wordclass_set.link(target='oed', defragment=True)
            node_id = wordclass_set.link(target='oed', as_tuple=True)[1]
            wcdata = WordclassData(wordclass_set.wordclass(),
                                   wordclass_set.frequency_table(),
                                   [],)
            for type_unit in [t for t in wordclass_set.types()
                              if t.has_frequency_table()]:
                typedata = TypeData(type_unit.form,
                                    type_unit.wordclass(),
                                    type_unit.frequency_table())
                wcdata.types.append(typedata)
            if wordclass_set.oed_entry_type() == 'entry':
                frequencies[oed_id].append(wcdata)
            else:
                subfrequencies[(oed_id, node_id)].append(wcdata)

    return frequencies, subfrequencies


def _construct_node(block, block_type, entry_id, node_id, label, parent_label,
                    frequency_blocks, terse):
    enode = etree.Element('e',
                          type=block_type,
                          xrid=str(entry_id),
                          xrnode=str(node_id),
                          obsolete=str(block.is_marked_obsolete()),
                          revised=str(block.is_revised),
                          firstDate=str(block.date().start),
                          lastDate=str(block.date().end))
    hwnode = etree.SubElement(enode, 'label')
    hwnode.text = label
    pnode = etree.SubElement(enode, 'parentLabel')
    pnode.text = parent_label
    lemnode = etree.SubElement(enode, 'lemma')
    lemnode.text = block.lemma
    defnode = etree.SubElement(enode, 'definition')
    defnode.text = block.definition(length=DEF_LENGTH, current=True)

    if frequency_blocks:
        # Create a frequency node for the entry as a whole, by
        # summing frequencies for each wordclass
        if len(frequency_blocks) > 1 or not terse:
            sumtable = sum_frequency_tables(
                [blockdata.frequency_table for blockdata in
                 frequency_blocks])
            enode.append(sumtable.to_xml())

        for blockdata in frequency_blocks:
            wordclass = blockdata.wordclass
            frequency_table = blockdata.frequency_table
            types = blockdata.types

            wcnode = etree.SubElement(enode, 'wordclass',
                                      penn=wordclass)
            if len(types) > 1 or not terse:
                wcnode.append(frequency_table.to_xml())
            wrapnode = etree.SubElement(wcnode, 'types')
            for typeunit in types:
                tnode = etree.SubElement(wrapnode, 'type',
                                         penn=typeunit.wordclass)
                z = etree.SubElement(tnode, 'form')
                z.text = typeunit.form
                tnode.append(typeunit.frequency_table.to_xml())

    return enode