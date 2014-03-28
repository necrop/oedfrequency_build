import csv
from lex.oed.resources.frequencyiterator import FrequencyIterator


def xml_to_csv(in_dir, out_file):
    iterator = FrequencyIterator(in_dir=in_dir, message='Populating .csv file')
    entries = []
    for e in iterator.iterate():
        if not e.has_frequency_table():
            continue

        frequency = e.frequency_table().frequency(period='modern')
        band = e.frequency_table().band(period='modern')
        label = e.label
        entry_id = e.id
        if e.is_main_entry:
            node_id = None
        else:
            node_id = e.xrnode

        row = (entry_id, node_id, label, frequency, band)
        entries.append(row)

    with open(out_file, 'w') as filehandle:
        csvwriter = csv.writer(filehandle)
        csvwriter.writerows(entries)
